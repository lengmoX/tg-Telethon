
from typing import Optional
from tgf.data.config import Config
from api.services.telegram_client_manager import TelegramClientManager, get_telegram_client_manager
from tgf.core.client import TGClient
from tgf.data.database import Database

class TelegramService:
    def __init__(self, config: Config):
        self.config = config
        self.client_manager = get_telegram_client_manager()

    async def get_client(self) -> Optional[TGClient]:
        """Get connected client"""
        return await self.client_manager.get_client()

    async def ensure_connected(self, db: Database) -> Optional[TGClient]:
        """Ensure connected to active account"""
        return await self.client_manager.ensure_active_account(db)
