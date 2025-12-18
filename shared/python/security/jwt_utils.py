from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from jose import jwt, JWTError
import logging

logger = logging.getLogger(__name__)

def create_access_token(data: Dict[str, Any], secret_key: str, algorithm: str, expires_delta: Optional[timedelta] = None) -> str:
    """
    Create a new JWT access token.
    """
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=15)
    
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, secret_key, algorithm=algorithm)
    return encoded_jwt

def decode_access_token(token: str, secret_key: str, algorithm: str) -> Optional[Dict[str, Any]]:
    """
    Decode and verify a JWT access token.
    Returns the payload if valid, None otherwise.
    """
    try:
        payload = jwt.decode(token, secret_key, algorithms=[algorithm])
        return payload
    except JWTError as e:
        logger.warning(f"JWT Decode Error: {e}")
        return None
