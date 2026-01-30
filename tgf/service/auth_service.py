"""
Authentication Service for TGF

Handles login, logout, and session management.
"""

from typing import Optional, Callable, List
from dataclasses import dataclass

from telethon.tl.types import User

from tgf.core.client import TGClient
from tgf.data.config import Config, get_config
from tgf.data.session import SessionManager
from tgf.utils.logger import get_logger
from tgf.utils.exceptions import AuthError


@dataclass
class AccountInfo:
    """Information about a logged-in account"""
    namespace: str
    user_id: int
    first_name: str
    last_name: Optional[str]
    username: Optional[str]
    phone: Optional[str]
    is_premium: bool = False


class AuthService:
    """Service for authentication operations"""
    
    def __init__(self, config: Optional[Config] = None):
        self.config = config or get_config()
        self.logger = get_logger("tgf.auth")
        self._session_manager = SessionManager(self.config.sessions_dir)
    
    async def login(
        self,
        namespace: str = "default",
        on_qr: Optional[Callable[[str], None]] = None,
        on_2fa: Optional[Callable[[], str]] = None
    ) -> AccountInfo:
        """
        Login with QR code
        
        Args:
            namespace: Account namespace
            on_qr: Callback for QR code URL display
            on_2fa: Callback to get 2FA password (returns str)
        
        Returns:
            AccountInfo for logged-in user
        """
        client = TGClient(self.config, namespace)
        
        try:
            # Check if already logged in
            connected = await client.connect()
            
            if connected:
                user = await client.get_me()
                self.logger.info(f"Already logged in as: {user.first_name}")
                return self._user_to_account_info(user, namespace)
            
            # Need to login
            user = await client.login_qr(on_qr=on_qr, on_2fa=on_2fa)
            return self._user_to_account_info(user, namespace)
            
        finally:
            await client.disconnect()
    
    async def logout(self, namespace: str = "default") -> bool:
        """
        Logout from an account
        
        Args:
            namespace: Account namespace to logout
        
        Returns:
            True if logout successful
        """
        client = TGClient(self.config, namespace)
        
        try:
            await client.connect()
            result = await client.logout()
            self.logger.info(f"Logged out from namespace: {namespace}")
            return result
        except Exception as e:
            self.logger.warning(f"Logout error: {e}")
            # Delete session file anyway
            return self._session_manager.delete_session(namespace)
    
    async def check_login(self, namespace: str = "default") -> Optional[AccountInfo]:
        """
        Check if account is logged in
        
        Args:
            namespace: Account namespace to check
        
        Returns:
            AccountInfo if logged in, None otherwise
        """
        if not self._session_manager.session_exists(namespace):
            return None
        
        client = TGClient(self.config, namespace)
        
        try:
            connected = await client.connect()
            
            if connected:
                user = await client.get_me()
                return self._user_to_account_info(user, namespace)
            
            return None
        except Exception:
            return None
        finally:
            await client.disconnect()
    
    def list_accounts(self) -> List[str]:
        """
        List all available account namespaces
        
        Returns:
            List of namespace names
        """
        return self._session_manager.list_sessions()
    
    async def get_account_info(self, namespace: str = "default") -> Optional[AccountInfo]:
        """
        Get detailed account info
        
        Args:
            namespace: Account namespace
        
        Returns:
            AccountInfo or None if not logged in
        """
        return await self.check_login(namespace)
    
    def _user_to_account_info(self, user: User, namespace: str) -> AccountInfo:
        """Convert Telethon User to AccountInfo"""
        return AccountInfo(
            namespace=namespace,
            user_id=user.id,
            first_name=user.first_name or "",
            last_name=user.last_name,
            username=user.username,
            phone=user.phone,
            is_premium=getattr(user, 'premium', False)
        )
