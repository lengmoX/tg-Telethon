"""
Configuration Management for TGF

Handles:
- Data directory paths
- API credentials
- Environment variables
- .env file loading
"""

import os
from pathlib import Path
from dataclasses import dataclass, field
from typing import Optional

# Try to import python-dotenv
try:
    from dotenv import load_dotenv
    HAS_DOTENV = True
except ImportError:
    HAS_DOTENV = False


@dataclass
class Config:
    """Global configuration for TGF"""
    
    # Default data directory: ~/.tgf
    data_dir: Path = field(default_factory=lambda: Path.home() / ".tgf")
    
    # Telegram API credentials (from https://my.telegram.org)
    api_id: Optional[int] = None
    api_hash: Optional[str] = None
    
    # Default namespace for multi-account support
    namespace: str = "default"
    
    # Logging
    log_level: str = "INFO"
    log_file: Optional[Path] = None
    
    # Forward settings
    default_mode: str = "clone"  # clone or direct
    default_interval: int = 30  # minutes
    
    # Retry settings
    max_retries: int = 5
    retry_min_delay: float = 5.0
    retry_max_delay: float = 10.0
    
    def __post_init__(self):
        """Load config from .env file and environment variables"""
        self._load_dotenv()
        self._load_from_env()
        self._ensure_directories()
    
    def _load_dotenv(self):
        """Load .env file if it exists"""
        if not HAS_DOTENV:
            return
        
        # Search for .env file in multiple locations
        search_paths = [
            Path.cwd() / ".env",                    # Current directory
            Path(__file__).parent.parent.parent / ".env",  # Project root
            self.data_dir / ".env",                 # Data directory
        ]
        
        for env_path in search_paths:
            if env_path.exists():
                load_dotenv(env_path)
                break
    
    def _load_from_env(self):
        """Load configuration from environment variables"""
        # TGF_DATA_DIR
        if env_data_dir := os.environ.get("TGF_DATA_DIR"):
            self.data_dir = Path(env_data_dir)
        
        # TGF_API_ID and TGF_API_HASH
        if api_id := os.environ.get("TGF_API_ID"):
            try:
                self.api_id = int(api_id)
            except ValueError:
                pass
        
        if api_hash := os.environ.get("TGF_API_HASH"):
            self.api_hash = api_hash
        
        # TGF_NAMESPACE
        if namespace := os.environ.get("TGF_NAMESPACE"):
            self.namespace = namespace
        
        # TGF_LOG_LEVEL
        if log_level := os.environ.get("TGF_LOG_LEVEL"):
            self.log_level = log_level.upper()
    
    def _ensure_directories(self):
        """Create necessary directories if they don't exist"""
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.sessions_dir.mkdir(parents=True, exist_ok=True)
        self.logs_dir.mkdir(parents=True, exist_ok=True)
    
    @property
    def sessions_dir(self) -> Path:
        """Directory for Telethon session files"""
        return self.data_dir / "sessions"
    
    @property
    def logs_dir(self) -> Path:
        """Directory for log files"""
        return self.data_dir / "logs"
    
    @property
    def db_path(self) -> Path:
        """Path to SQLite database file"""
        return self.data_dir / "tgf.db"
    
    def get_session_path(self, namespace: Optional[str] = None) -> Path:
        """Get session file path for a namespace"""
        ns = namespace or self.namespace
        return self.sessions_dir / f"{ns}.session"
    
    def has_credentials(self) -> bool:
        """Check if API credentials are configured"""
        return self.api_id is not None and self.api_hash is not None
    
    def set_namespace(self, namespace: str) -> "Config":
        """Create a new config with different namespace"""
        new_config = Config(
            data_dir=self.data_dir,
            api_id=self.api_id,
            api_hash=self.api_hash,
            namespace=namespace,
            log_level=self.log_level,
            log_file=self.log_file,
            default_mode=self.default_mode,
            default_interval=self.default_interval,
            max_retries=self.max_retries,
            retry_min_delay=self.retry_min_delay,
            retry_max_delay=self.retry_max_delay,
        )
        return new_config


# Global config instance
_config: Optional[Config] = None


def get_config() -> Config:
    """Get global config instance"""
    global _config
    if _config is None:
        _config = Config()
    return _config


def init_config(**kwargs) -> Config:
    """Initialize global config with custom settings"""
    global _config
    _config = Config(**kwargs)
    return _config
