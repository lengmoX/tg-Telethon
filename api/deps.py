"""
API Dependencies

Shared dependencies for dependency injection.
"""

import os
import hashlib
import secrets
from typing import Optional
from functools import lru_cache

from fastapi import Depends, HTTPException, status, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

from passlib.context import CryptContext

from tgf.data.config import Config, get_config
from tgf.data.database import Database


# ============== Config ==============

@lru_cache()
def get_api_config() -> Config:
    """Get cached config instance"""
    return get_config()


# ============== Database ==============

async def get_db(config: Config = Depends(get_api_config)) -> Database:
    """Get database connection"""
    db = Database(config.db_path)
    await db.connect()
    try:
        yield db
    finally:
        await db.close()


# ============== Auth ==============

# Password hashing context
pwd_context = CryptContext(schemes=["argon2"], deprecated="auto")

# Simple token-based auth
_active_tokens: dict[str, str] = {}  # token -> username

security = HTTPBearer(auto_error=False)


def get_password_hash(password: str) -> str:
    """Hash password with argon2"""
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify password against hash"""
    return pwd_context.verify(plain_password, hashed_password)


def create_token(username: str) -> str:
    """Create a new session token for user"""
    token = secrets.token_urlsafe(32)
    _active_tokens[token] = username
    return token


def revoke_token(token: str) -> bool:
    """Revoke a session token"""
    if token in _active_tokens:
        del _active_tokens[token]
        return True
    return False


def verify_token(token: str) -> Optional[str]:
    """Verify if token is valid and return username"""
    return _active_tokens.get(token)


async def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security)
) -> str:
    """Dependency to verify authentication"""
    if not credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    username = verify_token(credentials.credentials)
    if not username:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    return username


# Optional auth - allows unauthenticated access but provides user if authenticated
async def get_optional_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security)
) -> Optional[str]:
    """Optional authentication - returns None if not authenticated"""
    if not credentials:
        return None
    
    return verify_token(credentials.credentials)
