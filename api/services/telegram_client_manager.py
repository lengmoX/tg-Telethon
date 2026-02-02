"""
Telegram Client Manager - Shared Client Connection Pool

Provides a singleton client connection to avoid SQLite session locking issues.
The client stays connected and is reused across requests.
"""

import asyncio
import logging
from typing import Optional
from contextlib import asynccontextmanager

from tgf.core.client import TGClient
from tgf.data.config import Config

logger = logging.getLogger(__name__)


class TelegramClientManager:
    """
    Manages a shared Telegram client connection.
    
    Uses a singleton pattern to ensure only one client connection exists,
    preventing SQLite session file locking issues.
    """
    
    _instance: Optional['TelegramClientManager'] = None
    _lock = asyncio.Lock()
    
    def __init__(self):
        self._client: Optional[TGClient] = None
        self._config: Optional[Config] = None
        self._connected = False
        self._connect_lock = asyncio.Lock()
        self._usage_count = 0
    
    @classmethod
    def get_instance(cls) -> 'TelegramClientManager':
        """Get singleton instance"""
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance
    
    async def get_client(self, config: Config) -> TGClient:
        """
        Get a connected Telegram client.
        
        Creates and connects a client if not already connected.
        Reuses existing connection for subsequent calls.
        """
        async with self._connect_lock:
            # Check if we need to create/reconnect
            if self._client is None or not self._connected:
                logger.info("Creating new Telegram client connection...")
                self._config = config
                self._client = TGClient(config)
                
                try:
                    await self._client.connect()
                    self._connected = True
                    logger.info("Telegram client connected successfully")
                except Exception as e:
                    logger.error(f"Failed to connect Telegram client: {e}")
                    self._client = None
                    self._connected = False
                    raise
            
            self._usage_count += 1
            return self._client
    
    async def release_client(self):
        """Release client usage (for tracking, doesn't disconnect)"""
        self._usage_count = max(0, self._usage_count - 1)
    
    async def disconnect(self):
        """Disconnect the shared client"""
        async with self._connect_lock:
            if self._client and self._connected:
                logger.info("Disconnecting Telegram client...")
                try:
                    await self._client.disconnect()
                except Exception as e:
                    logger.warning(f"Error disconnecting client: {e}")
                finally:
                    self._connected = False
                    self._client = None
    
    @property
    def is_connected(self) -> bool:
        """Check if client is connected"""
        return self._connected and self._client is not None
    
    @property
    def usage_count(self) -> int:
        """Get current usage count"""
        return self._usage_count


# Global instance getter
def get_telegram_client_manager() -> TelegramClientManager:
    """Get the global Telegram client manager instance"""
    return TelegramClientManager.get_instance()


@asynccontextmanager
async def get_shared_client(config: Config):
    """
    Context manager for getting a shared Telegram client.
    
    Usage:
        async with get_shared_client(config) as client:
            dialogs = await client.get_dialogs()
    
    This avoids creating new connections per request and prevents
    SQLite session file locking issues.
    """
    manager = get_telegram_client_manager()
    client = await manager.get_client(config)
    try:
        yield client
    finally:
        await manager.release_client()
