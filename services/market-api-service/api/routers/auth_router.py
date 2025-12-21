from fastapi import APIRouter, Depends, HTTPException, Body
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from pydantic import BaseModel, EmailStr
from typing import Optional, Dict, Any

from services.auth_service import AuthService
from db.auth_repo import AuthRepository
from config.settings import settings

router = APIRouter()
auth_service = AuthService()

# --- Models ---
class UserRegister(BaseModel):
    email: EmailStr
    password: str
    full_name: Optional[str] = None

class Token(BaseModel):
    access_token: str
    token_type: str
    user: Dict[str, Any]

class OAuthLogin(BaseModel):
    provider: str
    token: str

class UserUpdate(BaseModel):
    full_name: Optional[str] = None
    avatar_url: Optional[str] = None
    password: Optional[str] = None
    current_password: Optional[str] = None

# --- Endpoints ---

from fastapi import BackgroundTasks


# --- Dependencies ---
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login")

from shared.python.security.jwt_utils import decode_access_token 
from fastapi import status

async def get_current_user(token: str = Depends(oauth2_scheme)):
    try:
        payload = decode_access_token(token, settings.JWT_SECRET, settings.JWT_ALGORITHM)
        user_id = payload.get("sub")
        if user_id is None:
             raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token payload")
        return user_id
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )

@router.post("/api/auth/register", tags=["Authentication"])
async def register(user: UserRegister, background_tasks: BackgroundTasks):
    """Register a new user."""
    return await auth_service.register_user(user.email, user.password, user.full_name, background_tasks)

@router.post("/api/auth/login", response_model=Token, tags=["Authentication"])
async def login(form_data: OAuth2PasswordRequestForm = Depends()):
    """Login with email and password (multipart/form-data)."""
    return auth_service.login_user(form_data.username, form_data.password)

@router.post("/api/auth/oauth/login", response_model=Token, tags=["Authentication"])
async def oauth_login(data: OAuthLogin):
    """Login with verified OAuth token (Google/Facebook)."""
    return await auth_service.login_with_oauth(data.provider, data.token)

class VerifyOTPRequest(BaseModel):
    email: EmailStr
    otp: str

class ResendOTPRequest(BaseModel):
    email: EmailStr

@router.post("/api/auth/resend-otp", tags=["Authentication"])
async def resend_otp(data: ResendOTPRequest, background_tasks: BackgroundTasks):
    """Resend verification OTP."""
    return await auth_service.resend_verification_otp(data.email, background_tasks)

@router.post("/api/auth/verify-otp", response_model=Token, tags=["Authentication"])
async def verify_otp(data: VerifyOTPRequest):
    """Verify OTP and return Access Token (Auto Login)."""
    return auth_service.verify_user_otp(data.email, data.otp)

@router.put("/api/auth/profile", tags=["Authentication"])
async def update_profile(
    updates: UserUpdate,
    current_user_id: str = Depends(get_current_user)
):
    """Update user profile (Name, Avatar, Password)."""
    # Convert Pydantic model to dict, excluding None values
    update_data = updates.dict(exclude_unset=True)
    
    if not update_data:
        raise HTTPException(status_code=400, detail="No updates provided")
        
    updated_user = auth_service.update_profile(current_user_id, update_data)
    if not updated_user:
        raise HTTPException(status_code=404, detail="User not found")
        
    return {
        "message": "Profile updated successfully",
        "user": {
            "full_name": updated_user.get("full_name"),
            "avatar_url": updated_user.get("avatar_url"),
            "email": updated_user.get("email")
        }
    }

class PasswordResetRequest(BaseModel):
    email: EmailStr

class PasswordResetConfirm(BaseModel):
    email: EmailStr
    otp: str
    new_password: str

@router.post("/api/auth/forgot-password", tags=["Authentication"])
async def forgot_password(data: PasswordResetRequest, background_tasks: BackgroundTasks):
    """Request password reset OTP."""
    return await auth_service.request_password_reset(data.email, background_tasks)

@router.post("/api/auth/reset-password", response_model=Token, tags=["Authentication"])
async def reset_password(data: PasswordResetConfirm):
    """Reset password with OTP and auto-login."""
    return auth_service.reset_password(data.email, data.otp, data.new_password)
