"""
Telegram Client Manager - Shared Client Connection Pool

Provides a singleton client connection to avoid SQLite session locking issues.
The client stays connected and is reused across requests.
"""

import asyncio
import logging
from typing import Optional
from pathlib import Path
from contextlib import asynccontextmanager

from tgf.core.client import TGClient
from tgf.data.config import Config, get_config
from tgf.data.database import Database

logger = logging.getLogger(__name__)


class TelegramClientManager:
    """
    Manages a shared Telegram client connection.
    Supports dynamic switching between accounts.
    """
    
    _instance: Optional['TelegramClientManager'] = None
    _lock = asyncio.Lock()
    
    def __init__(self):
        self._client: Optional[TGClient] = None
        self._connected = False
        self._connect_lock = asyncio.Lock()
        self._current_session_name: Optional[str] = None
    
    @classmethod
    def get_instance(cls) -> 'TelegramClientManager':
        """Get singleton instance"""
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance
    
    async def get_client(self) -> Optional[TGClient]:
        """Get the currently connected client"""
        if self._client and self._connected:
            return self._client
        return None
    
    async def switch_account(self, api_id: int, api_hash: str, session_name: str) -> TGClient:
        """
        Switch to a different account.
        Disconnects current client if connected and connects new one.
        """
        async with self._connect_lock:
            # If already connected to this session, return it
            if (self._client and self._connected and 
                self._current_session_name == session_name):
                return self._client
            
            # Disconnect current
            if self._client:
                logger.info(f"Disconnecting current session: {self._current_session_name}")
                try:
                    await self._client.disconnect()
                except Exception as e:
                    logger.warning(f"Error disconnecting client: {e}")
                finally:
                    self._client = None
                    self._connected = False
                    self._current_session_name = None
            
            # Connect new
            logger.info(f"Connecting to session: {session_name}")
            config = get_config()
            client = TGClient(
                config=config,
                namespace=session_name,
                api_id=api_id,
                api_hash=api_hash
            )
            
            await client.connect()
            self._client = client
            self._connected = True
            self._current_session_name = session_name
            
            return client

    async def ensure_active_account(self, db: Database) -> Optional[TGClient]:
        """
        Ensure the client is connected to the active account stored in DB.
        Should be called on startup or when needed.
        """
        active_account = await db.get_active_account()
        
        if not active_account:
            # No active account found, disconnect if connected
            if self._client:
                await self.disconnect()
            return None
        
        return await self.switch_account(
            api_id=active_account["api_id"],
            api_hash=active_account["api_hash"],
            session_name=active_account["session_name"]
        )

    async def disconnect(self):
        """Disconnect the shared client"""
        async with self._connect_lock:
            if self._client:
                logger.info("Disconnecting Telegram client...")
                try:
                    await self._client.disconnect()
                except Exception as e:
                    logger.warning(f"Error disconnecting client: {e}")
                finally:
                    self._connected = False
                    self._client = None
                    self._current_session_name = None
    
    @property
    def is_connected(self) -> bool:
        """Check if client is connected"""
        return self._connected and self._client is not None

    @property
    def current_session_name(self) -> Optional[str]:
        return self._current_session_name


# Global instance getter
def get_telegram_client_manager() -> TelegramClientManager:
    """Get the global Telegram client manager instance"""
    return TelegramClientManager.get_instance()


@asynccontextmanager
async def get_active_client_safe(db: Optional[Database] = None):
    """
    Context manager to get the active client.
    If db is provided, ensures persistence active account is loaded.
    """
    manager = get_telegram_client_manager()
    
    if db:
        # If we have DB access, ensure we are connected to the right account
        client = await manager.ensure_active_account(db)
    else:
        client = await manager.get_client()
        
    if not client:
        # Fallback or error? For now yield None and let caller handle
        yield None
    else:
        yield client

