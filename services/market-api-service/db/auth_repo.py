from datetime import datetime
from typing import Optional, Dict, Any
from .base_repo import BaseRepository
import logging

logger = logging.getLogger(__name__)

class AuthRepository(BaseRepository):
    """
    Repository for user authentication and identity management.
    interacts with `identity_oltp` schema.
    """

    def get_user_by_email(self, email: str) -> Optional[Dict[str, Any]]:
        query = """
            SELECT user_id, email, password_hash, full_name, is_verified, avatar_url, created_at
            FROM identity_oltp.users
            WHERE email = %s
        """
        return self.execute_query(query, (email,), fetch_one=True)

    def get_user_by_id(self, user_id: str) -> Optional[Dict[str, Any]]:
        query = """
            SELECT user_id, email, password_hash, full_name, is_verified, avatar_url, created_at
            FROM identity_oltp.users
            WHERE user_id = %s
        """
        return self.execute_query(query, (user_id,), fetch_one=True)

    def create_user(self, email: str, password_hash: Optional[str] = None, full_name: Optional[str] = None) -> Optional[Dict[str, Any]]:
        query = """
            INSERT INTO identity_oltp.users (email, password_hash, full_name)
            VALUES (%s, %s, %s)
            RETURNING user_id, email, full_name, created_at
        """
        return self.execute_query(query, (email, password_hash, full_name), fetch_one=True)

    def update_user_profile(self, user_id: str, updates: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Dynamically update user profile fields.
        """
        if not updates:
            return None
            
        set_clauses = []
        params = []
        for key, value in updates.items():
            set_clauses.append(f"{key} = %s")
            params.append(value)
            
        params.append(user_id)
        
        query = f"""
            UPDATE identity_oltp.users
            SET {', '.join(set_clauses)}
            WHERE user_id = %s
            RETURNING user_id, email, full_name, is_verified, avatar_url, updated_at
        """
        
        return self.execute_query(query, tuple(params), fetch_one=True)

    def verify_user_email(self, user_id: str) -> bool:
        query = "UPDATE identity_oltp.users SET is_verified = TRUE WHERE user_id = %s"
        try:
            self.execute_query(query, (user_id,))
            return True
        except Exception as e:
            logger.error(f"Error verifying user {user_id}: {e}")
            return False

    def store_verification_token(self, user_id: str, token: str, expires_at: datetime) -> bool:
        query = """
            INSERT INTO identity_oltp.email_verification_tokens (user_id, token, expires_at)
            VALUES (%s, %s, %s)
        """
        try:
            self.execute_query(query, (user_id, token, expires_at))
            return True
        except Exception as e:
            logger.error(f"Error storing token for user {user_id}: {e}")
            return False

    def get_valid_token(self, user_id: str, token: str) -> Optional[Dict[str, Any]]:
        query = """
            SELECT token_id, token, expires_at
            FROM identity_oltp.email_verification_tokens
            WHERE user_id = %s AND token = %s AND expires_at > CURRENT_TIMESTAMP
            ORDER BY created_at DESC
            LIMIT 1
        """
        return self.execute_query(query, (user_id, token), fetch_one=True)
        
    def delete_tokens(self, user_id: str):
        query = "DELETE FROM identity_oltp.email_verification_tokens WHERE user_id = %s"
        try:
            self.execute_query(query, (user_id,))
        except Exception as e:
            logger.error(f"Error deleting tokens for user {user_id}: {e}")

    def create_oauth_account(self, user_id: str, provider: str, provider_user_id: str, access_token: str) -> bool:
        query = """
            INSERT INTO identity_oltp.oauth_accounts (user_id, provider, provider_user_id, access_token)
            VALUES (%s, %s, %s, %s)
            ON CONFLICT (provider, provider_user_id) DO UPDATE 
            SET access_token = EXCLUDED.access_token, created_at = CURRENT_TIMESTAMP
        """
        try:
            self.execute_query(query, (user_id, provider, provider_user_id, access_token))
            return True
        except Exception as e:
            logger.error(f"Error creating oauth account: {e}")
            return False

    def get_oauth_account(self, provider: str, provider_user_id: str) -> Optional[Dict[str, Any]]:
        query = """
            SELECT o.user_id, u.email, u.full_name
            FROM identity_oltp.oauth_accounts o
            JOIN identity_oltp.users u ON o.user_id = u.user_id
            WHERE o.provider = %s AND o.provider_user_id = %s
        """
        return self.execute_query(query, (provider, provider_user_id), fetch_one=True)
