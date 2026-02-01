"""
Telegram Auth Service
Handles asynchronous QR code login flow.
"""

import asyncio
from enum import Enum
from typing import Optional, Dict

from telethon import TelegramClient
from telethon.errors import SessionPasswordNeededError

from tgf.core.client import TGClient
from tgf.data.config import Config


class AuthState(str, Enum):
    IDLE = "IDLE"
    QR_READY = "QR_READY"
    WAITING_PASSWORD = "WAITING_PASSWORD"
    SUCCESS = "SUCCESS"
    FAILED = "FAILED"


class TelegramAuthService:
    def __init__(self):
        self._client: Optional[TGClient] = None
        self._qr_login = None
        self._state: AuthState = AuthState.IDLE
        self._qr_url: Optional[str] = None
        self._user_info: Optional[Dict] = None
        self._error: Optional[str] = None
        self._task: Optional[asyncio.Task] = None

    @property
    def state(self) -> AuthState:
        return self._state

    @property
    def qr_url(self) -> Optional[str]:
        return self._qr_url

    @property
    def user_info(self) -> Optional[Dict]:
        return self._user_info

    @property
    def error(self) -> Optional[str]:
        return self._error

    @property
    def is_connected(self) -> bool:
        return self._client and self._client.is_connected

    async def get_client(self, config: Config, namespace: str = "default") -> TGClient:
        if not self._client:
            self._client = TGClient(config, namespace)
            # Only connect if we suspect we might have a session
            # But for checking status, we need to connect
            await self._client.connect()
        return self._client

    async def check_login_status(self, config: Config, namespace: str = "default") -> bool:
        """Check if currently logged in"""
        client = await self.get_client(config, namespace)
        if await client.client.is_user_authorized():
            self._state = AuthState.SUCCESS
            me = await client.get_me()
            if me:
                self._user_info = {
                    "id": me.id,
                    "username": me.username,
                    "first_name": me.first_name,
                    "last_name": me.last_name,
                    "phone": me.phone,
                    "is_premium": getattr(me, "premium", False)
                }
            return True
        else:
            if self._state == AuthState.SUCCESS:
                # Was success, now not authorized? Reset
                self._state = AuthState.IDLE
                self._user_info = None
            return False

    async def start_login(self, config: Config, namespace: str = "default"):
        """Start QR login process"""
        if self._task and not self._task.done():
            # Already running
            return

        self._reset_state()
        client = await self.get_client(config, namespace)
        
        if await client.client.is_user_authorized():
            await self.check_login_status(config, namespace)
            return

        # Start background task
        self._task = asyncio.create_task(self._qr_login_loop(client.client))

    async def _qr_login_loop(self, client: TelegramClient):
        try:
            self._qr_login = await client.qr_login()
            self._qr_url = self._qr_login.url
            self._state = AuthState.QR_READY
            
            # Wait for scan
            try:
                user = await self._qr_login.wait(timeout=120)  # 2 minutes timeout
                self._state = AuthState.SUCCESS
                self._user_info = {
                    "id": user.id,
                    "username": user.username,
                    "first_name": user.first_name,
                    "last_name": user.last_name,
                    "phone": user.phone,
                    "is_premium": getattr(user, "premium", False)
                }
            except SessionPasswordNeededError:
                self._state = AuthState.WAITING_PASSWORD
            
        except asyncio.TimeoutError:
            self._state = AuthState.FAILED
            self._error = "QR code expired"
        except Exception as e:
            self._state = AuthState.FAILED
            self._error = str(e)
            
    async def submit_password(self, password: str):
        """Submit 2FA password"""
        if self._state != AuthState.WAITING_PASSWORD or not self._client:
            raise ValueError("Not waiting for password")
            
        try:
            user = await self._client.client.sign_in(password=password)
            self._state = AuthState.SUCCESS
            self._user_info = {
                "id": user.id,
                "username": user.username,
                "first_name": user.first_name,
                "last_name": user.last_name,
                "phone": user.phone,
                "is_premium": getattr(user, "premium", False)
            }
        except Exception as e:
            # Keep waiting for password if wrong
            self._error = f"Login failed: {str(e)}"
            # Don't change state to FAILED immediately, let retry?
            # Or maybe just return error
            raise e

    async def logout(self):
        """Logout"""
        if self._client and self._client.is_connected:
            await self._client.logout()
        self._reset_state()

    def _reset_state(self):
        self._state = AuthState.IDLE
        self._qr_url = None
        self._qr_login = None
        self._user_info = None
        self._error = None


# Singleton instance
auth_service = TelegramAuthService()
