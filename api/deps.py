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

# Simple token-based auth
# Password set via TGF_WEB_PASSWORD env var
_active_tokens: set[str] = set()

security = HTTPBearer(auto_error=False)


def get_password_hash(password: str) -> str:
    """Hash password with SHA256"""
    return hashlib.sha256(password.encode()).hexdigest()


def verify_password(password: str) -> bool:
    """Verify password against env var"""
    expected = os.environ.get("TGF_WEB_PASSWORD", "admin")
    return password == expected


def create_token() -> str:
    """Create a new session token"""
    token = secrets.token_urlsafe(32)
    _active_tokens.add(token)
    return token


def revoke_token(token: str) -> bool:
    """Revoke a session token"""
    if token in _active_tokens:
        _active_tokens.discard(token)
        return True
    return False


def verify_token(token: str) -> bool:
    """Verify if token is valid"""
    return token in _active_tokens


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
    
    if not verify_token(credentials.credentials):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    return "user"


# Optional auth - allows unauthenticated access but provides user if authenticated
async def get_optional_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security)
) -> Optional[str]:
    """Optional authentication - returns None if not authenticated"""
    if not credentials:
        return None
    
    if verify_token(credentials.credentials):
        return "user"
    
    return None
