"""
Telegram Client Wrapper for TGF

Wraps TelegramClient with QR code login and connection management.
"""

import asyncio
import io
from pathlib import Path
from typing import Optional, AsyncIterator, Union, List

from telethon import TelegramClient
from telethon.sessions import StringSession
from telethon.tl.types import User
from telethon.errors import SessionPasswordNeededError

import qrcode

from tgf.data.config import Config, get_config
from tgf.data.session import SessionManager
from tgf.utils.logger import get_logger
from tgf.utils.exceptions import AuthError, ConfigError


class TGClient:
    """Telegram Client wrapper with QR login and multi-account support"""
    
    def __init__(
        self,
        config: Optional[Config] = None,
        namespace: Optional[str] = None
    ):
        """
        Initialize TGClient
        
        Args:
            config: Configuration object (uses global config if None)
            namespace: Account namespace (uses config namespace if None)
        """
        self.config = config or get_config()
        self.namespace = namespace or self.config.namespace
        self.logger = get_logger("tgf.client")
        
        self._client: Optional[TelegramClient] = None
        self._session_manager = SessionManager(self.config.sessions_dir)
    
    @property
    def client(self) -> TelegramClient:
        """Get underlying TelegramClient"""
        if not self._client:
            raise AuthError("Client not initialized. Call connect() first.")
        return self._client
    
    @property
    def is_connected(self) -> bool:
        """Check if client is connected"""
        return self._client is not None and self._client.is_connected()
    
    def _ensure_credentials(self):
        """Ensure API credentials are configured"""
        if not self.config.has_credentials():
            raise ConfigError(
                "Telegram API credentials not configured. "
                "Set TGF_API_ID and TGF_API_HASH environment variables, "
                "or get credentials from https://my.telegram.org"
            )
    
    async def connect(self) -> bool:
        """
        Connect to Telegram
        
        Returns:
            True if connected and authorized, False otherwise
        """
        self._ensure_credentials()
        
        session_path = self._session_manager.get_session_path(self.namespace)
        
        self._client = TelegramClient(
            str(session_path),
            self.config.api_id,
            self.config.api_hash
        )
        
        await self._client.connect()
        
        if await self._client.is_user_authorized():
            self.logger.info(f"Connected as namespace: {self.namespace}")
            return True
        
        return False
    
    async def disconnect(self) -> None:
        """Disconnect from Telegram"""
        if self._client:
            await self._client.disconnect()
            self._client = None
    
    async def login_qr(
        self,
        on_qr: callable = None,
        on_2fa: callable = None
    ) -> User:
        """
        Login using QR code
        
        Args:
            on_qr: Callback function receiving QR code URL for display
            on_2fa: Callback function to get 2FA password (returns str)
                   If None, will prompt in terminal
        
        Returns:
            Logged in user
        """
        self._ensure_credentials()
        
        if not self._client:
            await self.connect()
        
        # Use QR code login
        qr_login = await self._client.qr_login()
        
        while True:
            # Generate QR code URL
            url = qr_login.url
            
            if on_qr:
                on_qr(url)
            else:
                self._print_qr(url)
            
            try:
                # Wait for user to scan QR code
                user = await qr_login.wait(timeout=30)
                self.logger.info(f"Logged in as: {user.first_name} (@{user.username or 'N/A'})")
                return user
                
            except SessionPasswordNeededError:
                # 2FA is enabled, need password
                self.logger.info("Two-step verification enabled, password required")
                
                if on_2fa:
                    password = on_2fa()
                else:
                    password = self._prompt_2fa_password()
                
                if not password:
                    raise AuthError("2FA password required but not provided")
                
                # Sign in with password
                user = await self._client.sign_in(password=password)
                self.logger.info(f"Logged in with 2FA as: {user.first_name}")
                return user
                
            except asyncio.TimeoutError:
                # Regenerate QR code
                await qr_login.recreate()
    
    def _prompt_2fa_password(self) -> str:
        """Prompt for 2FA password in terminal"""
        import getpass
        print("\n" + "=" * 40)
        print("Two-step verification is enabled")
        print("=" * 40)
        password = getpass.getpass("Enter your 2FA password: ")
        return password
    
    def _print_qr(self, url: str) -> None:
        """Print QR code to terminal"""
        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_L,
            box_size=1,
            border=1,
        )
        qr.add_data(url)
        qr.make(fit=True)
        
        # Print to terminal
        print("\n" + "=" * 40)
        print("Scan this QR code with Telegram app:")
        print("=" * 40)
        
        # Generate ASCII QR code
        f = io.StringIO()
        qr.print_ascii(out=f, invert=True)
        f.seek(0)
        print(f.read())
        
        print("=" * 40)
        print("Waiting for scan...")
    
    async def logout(self) -> bool:
        """
        Logout and delete session
        
        Returns:
            True if logout successful
        """
        if self._client and self._client.is_connected():
            await self._client.log_out()
        
        # Delete session file
        if self._session_manager.delete_session(self.namespace):
            self.logger.info(f"Session deleted: {self.namespace}")
            return True
        
        return False
    
    async def get_me(self) -> Optional[User]:
        """Get current user info"""
        if not self.is_connected:
            return None
        return await self._client.get_me()
    
    async def get_dialogs(self, limit: int = 100):
        """Get list of dialogs (chats)"""
        return await self._client.get_dialogs(limit=limit)
    
    async def get_entity(self, entity: Union[str, int]):
        """
        Get entity by username/ID/link
        
        Args:
            entity: Username (@channel), ID, or t.me link
                    Supports: @username, username, 123456789, -100xxx, 
                    https://t.me/xxx, +phone, "me" for saved messages
        
        Returns:
            Entity object (User, Chat, Channel)
        """
        # Handle "me" keyword for Saved Messages
        if isinstance(entity, str):
            if entity.lower() == "me":
                return await self._client.get_me()
            
            # Try to parse as integer
            entity_str = entity.strip()
            if entity_str.lstrip('-').isdigit():
                entity = int(entity_str)
        
        # For numeric IDs, try multiple formats
        if isinstance(entity, int):
            return await self._resolve_numeric_id(entity)
        
        # For strings (username, link), use direct lookup
        return await self._client.get_entity(entity)
    
    async def _resolve_numeric_id(self, entity_id: int):
        """
        Resolve numeric ID to entity
        
        Telegram uses different ID formats:
        - User IDs: positive numbers (e.g., 123456789)
        - Groups: negative numbers (e.g., -123456789)
        - Channels/Supergroups: -100 prefix (e.g., -1001234567890)
        """
        from telethon.tl.types import PeerUser, PeerChat, PeerChannel
        from telethon import utils
        
        # If already negative (properly formatted), try directly
        if entity_id < 0:
            try:
                return await self._client.get_entity(entity_id)
            except Exception:
                pass
        
        # Try as-is first (might be a user ID)
        try:
            return await self._client.get_entity(entity_id)
        except Exception:
            pass
        
        # Try with -100 prefix for channels/supergroups
        if entity_id > 0:
            channel_id = int(f"-100{entity_id}")
            try:
                return await self._client.get_entity(channel_id)
            except Exception:
                pass
            
            # Try as regular group (negative without -100)
            try:
                return await self._client.get_entity(-entity_id)
            except Exception:
                pass
        
        # Last resort: search in dialogs
        try:
            dialogs = await self._client.get_dialogs(limit=500)
            for d in dialogs:
                if d.entity.id == entity_id or d.entity.id == abs(entity_id):
                    return d.entity
                # Check with -100 stripped
                full_id = str(d.entity.id)
                if full_id.startswith("-100") and full_id[4:] == str(entity_id):
                    return d.entity
        except Exception:
            pass
        
        raise ValueError(f'Cannot find any entity corresponding to "{entity_id}"')
    
    async def iter_messages(
        self,
        entity,
        limit: Optional[int] = None,
        min_id: int = 0,
        max_id: int = 0,
        reverse: bool = False,
        **kwargs
    ) -> AsyncIterator:
        """
        Iterate over messages in a chat
        
        Args:
            entity: Chat/channel to get messages from
            limit: Maximum number of messages
            min_id: Minimum message ID (get messages > min_id)
            max_id: Maximum message ID (get messages < max_id)
            reverse: If True, return oldest first
        
        Yields:
            Message objects
        """
        async for message in self._client.iter_messages(
            entity,
            limit=limit,
            min_id=min_id,
            max_id=max_id,
            reverse=reverse,
            **kwargs
        ):
            yield message
    
    async def get_messages(
        self,
        entity,
        ids: Optional[List[int]] = None,
        limit: Optional[int] = None,
        **kwargs
    ):
        """Get messages by IDs or with limit"""
        return await self._client.get_messages(
            entity,
            ids=ids,
            limit=limit,
            **kwargs
        )
    
    async def send_message(self, entity, message: str = "", **kwargs):
        """Send a message"""
        return await self._client.send_message(entity, message, **kwargs)
    
    async def send_file(self, entity, file, **kwargs):
        """Send a file"""
        return await self._client.send_file(entity, file, **kwargs)
    
    async def forward_messages(self, entity, messages, from_peer, **kwargs):
        """Forward messages (native forward with header)"""
        return await self._client.forward_messages(entity, messages, from_peer, **kwargs)
    
    async def download_media(self, message, file=None, **kwargs):
        """Download media from message"""
        return await self._client.download_media(message, file, **kwargs)
    
    async def __aenter__(self):
        await self.connect()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.disconnect()
