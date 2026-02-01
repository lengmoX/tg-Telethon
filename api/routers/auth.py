"""
Authentication Router
"""

from fastapi import APIRouter, HTTPException, status

from api.schemas import LoginRequest, TokenResponse, MessageResponse
from api.deps import verify_password, create_token, revoke_token


router = APIRouter()


@router.post("/login", response_model=TokenResponse)
async def login(request: LoginRequest):
    """
    Login with password and get access token
    
    Password is configured via TGF_WEB_PASSWORD environment variable.
    Default password is 'admin'.
    """
    if not verify_password(request.password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect password"
        )
    
    token = create_token()
    return TokenResponse(access_token=token)


@router.post("/logout", response_model=MessageResponse)
async def logout(token: str):
    """Logout and revoke token"""
    revoke_token(token)
    return MessageResponse(message="Logged out successfully")
