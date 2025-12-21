from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from passlib.context import CryptContext
from fastapi import HTTPException, status, BackgroundTasks
from fastapi_mail import FastMail, MessageSchema, ConnectionConfig, MessageType
import httpx
import logging

from config.settings import settings
from db.auth_repo import AuthRepository
from shared.python.security.jwt_utils import create_access_token

logger = logging.getLogger(__name__)

pwd_context = CryptContext(schemes=["pbkdf2_sha256"], deprecated="auto")

# Email Config
# Email Config
try:
    if settings.MAIL_USERNAME and settings.MAIL_SERVER:
        conf = ConnectionConfig(
            MAIL_USERNAME=settings.MAIL_USERNAME,
            MAIL_PASSWORD=settings.MAIL_PASSWORD,
            MAIL_FROM=settings.MAIL_FROM or settings.MAIL_USERNAME,
            MAIL_PORT=settings.MAIL_PORT,
            MAIL_SERVER=settings.MAIL_SERVER,
            MAIL_STARTTLS=True,
            MAIL_SSL_TLS=False,
            USE_CREDENTIALS=True,
            VALIDATE_CERTS=True
        )
    else:
        conf = None
except Exception as e:
    logger.warning(f"Failed to initialize email config: {e}")
    conf = None

class AuthService:
    def __init__(self):
        self.repo = AuthRepository()

    def get_password_hash(self, password: str) -> str:
        return pwd_context.hash(password)

    def verify_password(self, plain_password: str, hashed_password: str) -> bool:
        return pwd_context.verify(plain_password, hashed_password)

    async def send_verification_email(self, email: str, otp: str):
        # VERBOSE DEBUG LOGGING
        logger.info(f"--- DEBUG SMTP START ---")
        logger.info(f"Settings: USER='{settings.MAIL_USERNAME}' SERVER='{settings.MAIL_SERVER}' PORT={settings.MAIL_PORT}")
        logger.info(f"Password Check: {'Fail (None)' if not settings.MAIL_PASSWORD else f'OK (Len={len(settings.MAIL_PASSWORD)})'}")
        
        # Re-initialize conf here to be absolutely sure we catch runtime env changes
        try:
             local_conf = ConnectionConfig(
                MAIL_USERNAME=settings.MAIL_USERNAME,
                MAIL_PASSWORD=settings.MAIL_PASSWORD,
                MAIL_FROM=settings.MAIL_FROM or settings.MAIL_USERNAME,
                MAIL_PORT=settings.MAIL_PORT,
                MAIL_SERVER=settings.MAIL_SERVER,
                MAIL_STARTTLS=True,
                MAIL_SSL_TLS=False,
                USE_CREDENTIALS=True,
                VALIDATE_CERTS=True
            )
             logger.info("Config Object Created Successfully")
             print(f"DEBUG: Config created. Server={settings.MAIL_SERVER}, User={settings.MAIL_USERNAME}") # DIRECT PRINT
        except Exception as e:
            logger.error(f"Config Creation Failed: {e}")
            local_conf = None

        if not local_conf:
            logger.error("CRITICAL: SMTP Config is None. Falling back to MOCK.")
            logger.warning("SMTP not configured or failed to initialize. Skipping email sending.")
            logger.info(f"MOCK OTP CODE: {otp}")
            return

        message = MessageSchema(
            subject="Snowball Stock App - Verification Code",
            recipients=[email],
            body=f"""
            <h1>Welcome to Snowball!</h1>
            <p>Your verification code is:</p>
            <h2 style="color: #4CAF50; letter-spacing: 5px;">{otp}</h2>
            <p>This code expires in 15 minutes.</p>
            """,
            subtype=MessageType.html
        )

        try:
            logger.info(f"Attempting to send email to {email}...")
            fm = FastMail(local_conf)
            await fm.send_message(message)
            logger.info("--- EMAIL SENT SUCCESSFULLY ---")
        except Exception as e:
            logger.error(f"--- EMAIL SENDING FAILED: {e} ---")

    async def register_user(self, email: str, password: str, full_name: Optional[str] = None, background_tasks: BackgroundTasks = None) -> Dict[str, Any]:
        existing_user = self.repo.get_user_by_email(email)
        user_id = None
        
        if existing_user:
            if existing_user["is_verified"]:
                raise HTTPException(status_code=400, detail="Email already registered")
            else:
                # User exists but NOT verified -> Allow overwrite (Re-registration)
                logger.info(f"Overwriting unverified user: {email}")
                hashed_password = self.get_password_hash(password)
                
                # Update password and info
                updates = {"password_hash": hashed_password}
                if full_name:
                    updates["full_name"] = full_name
                    
                self.repo.update_user_profile(existing_user['user_id'], updates)
                user_id = existing_user['user_id']
                
                # We reuse the existing user object for response, but update fields
                new_user = existing_user
                new_user.update(updates) # basic dict update for return
        else:
            # New User
            hashed_password = self.get_password_hash(password)
            new_user = self.repo.create_user(email, hashed_password, full_name)
            user_id = new_user['user_id']
        
        # Generate 6-digit OTP
        import random
        otp = f"{random.randint(100000, 999999)}"
        expires_at = datetime.now() + timedelta(minutes=15)
        
        # Store OTP in DB
        self.repo.store_verification_token(user_id, otp, expires_at)
        
        if background_tasks:
            background_tasks.add_task(self.send_verification_email, email, otp)
        else:
            await self.send_verification_email(email, otp)
        
        return new_user

    async def resend_verification_otp(self, email: str, background_tasks: BackgroundTasks = None):
        user = self.repo.get_user_by_email(email)
        if not user:
             raise HTTPException(status_code=400, detail="User not found")
        
        if user["is_verified"]:
             raise HTTPException(status_code=400, detail="User already verified")

        # Generate new 6-digit OTP
        import random
        otp = f"{random.randint(100000, 999999)}"
        expires_at = datetime.now() + timedelta(minutes=15)
        
        # Store OTP in DB
        self.repo.store_verification_token(user['user_id'], otp, expires_at)
        
        if background_tasks:
            background_tasks.add_task(self.send_verification_email, email, otp)
        else:
            await self.send_verification_email(email, otp)
            
        return {"message": "OTP resent successfully"}

    def verify_user_otp(self, email: str, otp: str) -> Dict[str, Any]:
        # 1. Find user
        user = self.repo.get_user_by_email(email)
        if not user:
             raise HTTPException(status_code=400, detail="User not found")
             
        if user["is_verified"]:
             # Already verified, just login
             pass
        else:
            # 2. Check token
            valid_token = self.repo.get_valid_token(user['user_id'], otp)
            if not valid_token:
                raise HTTPException(status_code=400, detail="Invalid or expired OTP")
                
            # 3. Mark verified
            self.repo.verify_user_email(user['user_id'])
            
            # 4. Cleanup tokens
            self.repo.delete_tokens(user['user_id'])
            
        # 5. Generate Auth Token (Login)
        access_token_expires = timedelta(minutes=settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES)
        access_token = create_access_token(
            data={"sub": str(user["user_id"]), "email": user["email"]},
            secret_key=settings.JWT_SECRET,
            algorithm=settings.JWT_ALGORITHM
        )
        
        return {
            "access_token": access_token, 
            "token_type": "bearer",
            "user": {
                "id": str(user["user_id"]),
                "email": user["email"],
                "full_name": user["full_name"],
                "avatar_url": user["avatar_url"], 
                "is_verified": True
            }
        }

    def login_user(self, email: str, password: str) -> Dict[str, Any]:
        user = self.repo.get_user_by_email(email)
        if not user or not user["password_hash"]:
            raise HTTPException(status_code=401, detail="Invalid email or password")
        
        if not self.verify_password(password, user["password_hash"]):
            raise HTTPException(status_code=401, detail="Invalid email or password")

        if not user.get("is_verified"):
            raise HTTPException(status_code=403, detail="Email not verified. Please check your inbox.")
            
        access_token_expires = timedelta(minutes=settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES)
        access_token = create_access_token(
            data={"sub": str(user["user_id"]), "email": user["email"]},
            secret_key=settings.JWT_SECRET,
            algorithm=settings.JWT_ALGORITHM
        )
        
        return {
            "access_token": access_token, 
            "token_type": "bearer",
            "user": {
                "id": str(user["user_id"]),
                "email": user["email"],
                "full_name": user["full_name"],
                "avatar_url": user["avatar_url"], 
                "is_verified": user["is_verified"]
            }
        }

    async def verify_google_token(self, token: str) -> Dict[str, Any]:
        async with httpx.AsyncClient() as client:
            response = await client.get(f"https://www.googleapis.com/oauth2/v3/userinfo?access_token={token}")
            if response.status_code != 200:
                raise HTTPException(status_code=400, detail="Invalid Google token")
            return response.json()

    async def verify_facebook_token(self, token: str) -> Dict[str, Any]:
        async with httpx.AsyncClient() as client:
            response = await client.get(f"https://graph.facebook.com/me?fields=id,name,email,picture&access_token={token}")
            if response.status_code != 200:
                raise HTTPException(status_code=400, detail="Invalid Facebook token")
            return response.json()

    async def login_with_oauth(self, provider: str, token: str) -> Dict[str, Any]:
        if provider == "google":
            user_info = await self.verify_google_token(token)
            email = user_info.get("email")
            provider_user_id = user_info.get("sub")
            full_name = user_info.get("name")
            avatar_url = user_info.get("picture")
        elif provider == "facebook":
            user_info = await self.verify_facebook_token(token)
            email = user_info.get("email")
            provider_user_id = user_info.get("id")
            full_name = user_info.get("name")
            avatar_url = user_info.get("picture", {}).get("data", {}).get("url")
        else:
            raise HTTPException(status_code=400, detail="Unsupported provider")

        if not email:
            raise HTTPException(status_code=400, detail="Email not provided by provider")

        # Fallback name if missing
        if not full_name:
            full_name = email.split("@")[0]

        # Check update or create user
        user = self.repo.get_user_by_email(email)
        updates = {}
        
        if not user:
            user = self.repo.create_user(email, password_hash=None, full_name=full_name)
            if avatar_url:
                updates["avatar_url"] = avatar_url
        else:
            # Sync info for existing user
            # Always update avatar if new one is from OAuth
            if avatar_url and user.get("avatar_url") != avatar_url:
                updates["avatar_url"] = avatar_url
            
            # Update name if missing in DB
            if full_name and not user.get("full_name"):
                 updates["full_name"] = full_name
        
        if updates:
             updated_user = self.repo.update_user_profile(user['user_id'], updates)
             if updated_user:
                 user.update(updated_user)

        # Link OAuth
        self.repo.create_oauth_account(user["user_id"], provider, provider_user_id, token)

        # Generate Token
        access_token_expires = timedelta(minutes=settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES)
        access_token = create_access_token(
            data={"sub": str(user["user_id"]), "email": user["email"]},
            secret_key=settings.JWT_SECRET,
            algorithm=settings.JWT_ALGORITHM
        )

        return {
            "access_token": access_token, 
            "token_type": "bearer",
            "user": {
                "id": str(user["user_id"]),
                "email": user["email"],
                "full_name": user["full_name"],
                "avatar_url": user.get("avatar_url"),
                "is_verified": user.get("is_verified", False)
            }
        }
        
    def update_profile(self, user_id: str, updates: Dict[str, Any]):
        # Preventupdating restricted fields here if needed, e.g email
        if "password" in updates:
            new_password = updates.pop("password")
            current_password = updates.pop("current_password", None)
            
            # Fetch user to check existing password
            user = self.repo.get_user_by_id(user_id)
            if not user:
                 raise HTTPException(status_code=404, detail="User not found")

            # If user has a password, they MUST provide current_password
            if user.get("password_hash"):
                if not current_password:
                     raise HTTPException(status_code=400, detail="Current password is required to set a new password.")
                
                if not self.verify_password(current_password, user["password_hash"]):
                     raise HTTPException(status_code=400, detail="Incorrect current password.")

            updates["password_hash"] = self.get_password_hash(new_password)
             
        return self.repo.update_user_profile(user_id, updates)

    async def request_password_reset(self, email: str, background_tasks: BackgroundTasks = None):
        user = self.repo.get_user_by_email(email)
        if not user:
             # For security, we might want to return 200 even if email not found, 
             # but strictly for this app dev let's be explicit
             raise HTTPException(status_code=404, detail="User not found")

        # Generate OTP
        import random
        otp = f"{random.randint(100000, 999999)}"
        expires_at = datetime.now() + timedelta(minutes=15)
        
        # Store OTP (Reusing same token table)
        self.repo.store_verification_token(user['user_id'], otp, expires_at)
        
        # HTML Email Body for Reset
        message = MessageSchema(
            subject="Snowball Stock App - Password Reset Request",
            recipients=[email],
            body=f"""
            <h1>Password Reset Request</h1>
            <p>You requested to reset your password. Use the code below:</p>
            <h2 style="color: #FF5722; letter-spacing: 5px;">{otp}</h2>
            <p>This code expires in 15 minutes. If you did not request this, please ignore this email.</p>
            """,
            subtype=MessageType.html
        )

        async def send_email_task():
            # ... reused email logic ...
            # TODO: Refactor send_verification_email to accept body/subject to avoid duplicating code.
            # For now, duplicate simpler version or just format reuse.
            # To avoid large refactors now:
            
            # Re-initialize conf logic (duplicated for safety as seen before)
            # ... (omitted for brevity, relying on a helper or direct send if possible)
            # Actually, let's just use a helper if we can, or copy the connection init.
            # Since 'send_verification_email' is hardcoded, I'll inline the send here.
            
            try:
                local_conf = ConnectionConfig(
                    MAIL_USERNAME=settings.MAIL_USERNAME,
                    MAIL_PASSWORD=settings.MAIL_PASSWORD,
                    MAIL_FROM=settings.MAIL_FROM or settings.MAIL_USERNAME,
                    MAIL_PORT=settings.MAIL_PORT,
                    MAIL_SERVER=settings.MAIL_SERVER,
                    MAIL_STARTTLS=True,
                    MAIL_SSL_TLS=False,
                    USE_CREDENTIALS=True,
                    VALIDATE_CERTS=True
                )
                fm = FastMail(local_conf)
                await fm.send_message(message)
                logger.info("--- RESET PASSWORD EMAIL SENT ---")
            except Exception as e:
                logger.error(f"--- RESET EMAIL FAILED: {e} ---")
                # Mock if failed
                logger.info(f"MOCK RESET OTP: {otp}")

        if background_tasks:
            background_tasks.add_task(send_email_task)
        else:
            await send_email_task()
            
        return {"message": "Password reset OTP sent"}

    def reset_password(self, email: str, otp: str, new_password: str) -> Dict[str, Any]:
        user = self.repo.get_user_by_email(email)
        if not user:
             raise HTTPException(status_code=404, detail="User not found")
        
        # Check Token
        valid_token = self.repo.get_valid_token(user['user_id'], otp)
        if not valid_token:
            raise HTTPException(status_code=400, detail="Invalid or expired OTP")
            
        # Update Password
        hashed_password = self.get_password_hash(new_password)
        self.repo.update_user_profile(user['user_id'], {"password_hash": hashed_password})
        
        # Cleanup
        self.repo.delete_tokens(user['user_id'])
        
        # Auto Login
        return self.login_user(email, new_password)
