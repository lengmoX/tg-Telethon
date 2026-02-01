"""
Telegram Auth Router
"""

from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks

from api.schemas import (
    TelegramAuthStatus, 
    TelegramUser, 
    MessageResponse, 
    TelegramPasswordRequest
)
from api.deps import get_api_config, get_current_user
from api.services.telegram_auth import auth_service, AuthState
from tgf.data.config import Config


router = APIRouter()


@router.get("/status", response_model=TelegramAuthStatus)
async def get_status(
    config: Config = Depends(get_api_config),
    _: str = Depends(get_current_user)
):
    """Get current login status"""
    # If IDLE, check if we have a valid session file
    if auth_service.state == AuthState.IDLE:
        # This will update status to SUCCESS if session exists
        await auth_service.check_login_status(config)
    
    return TelegramAuthStatus(
        logged_in=auth_service.state == AuthState.SUCCESS,
        state=auth_service.state.value,
        qr_url=auth_service.qr_url,
        user=TelegramUser(**auth_service.user_info) if auth_service.user_info else None,
        error=auth_service.error
    )


@router.post("/login", response_model=TelegramAuthStatus)
async def login(
    background_tasks: BackgroundTasks,
    config: Config = Depends(get_api_config),
    _: str = Depends(get_current_user)
):
    """Start QR login process"""
    await auth_service.start_login(config)
    
    return TelegramAuthStatus(
        logged_in=auth_service.state == AuthState.SUCCESS,
        state=auth_service.state.value,
        qr_url=auth_service.qr_url,
        user=TelegramUser(**auth_service.user_info) if auth_service.user_info else None,
        error=auth_service.error
    )


@router.post("/password", response_model=TelegramAuthStatus)
async def submit_password(
    request: TelegramPasswordRequest,
    _: str = Depends(get_current_user)
):
    """Submit 2FA password"""
    if auth_service.state != AuthState.WAITING_PASSWORD:
        raise HTTPException(status_code=400, detail="Not waiting for password")
    
    try:
        await auth_service.submit_password(request.password)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
        
    return TelegramAuthStatus(
        logged_in=auth_service.state == AuthState.SUCCESS,
        state=auth_service.state.value,
        qr_url=auth_service.qr_url,
        user=TelegramUser(**auth_service.user_info) if auth_service.user_info else None,
        error=auth_service.error
    )


@router.post("/logout", response_model=MessageResponse)
async def logout(
    _: str = Depends(get_current_user)
):
    """Logout from Telegram"""
    await auth_service.logout()
    return MessageResponse(message="Logged out from Telegram")
