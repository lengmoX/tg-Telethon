"""
Session Management for TGF

Handles Telethon session files for multi-account support.
"""

from pathlib import Path
from typing import Optional, List
import shutil


class SessionManager:
    """Manage Telethon session files for multiple accounts/namespaces"""
    
    def __init__(self, sessions_dir: Path):
        self.sessions_dir = sessions_dir
        self.sessions_dir.mkdir(parents=True, exist_ok=True)
    
    def get_session_path(self, namespace: str) -> Path:
        """Get session file path for a namespace (without .session extension)"""
        return self.sessions_dir / namespace
    
    def get_session_file(self, namespace: str) -> Path:
        """Get full session file path with .session extension"""
        return self.sessions_dir / f"{namespace}.session"
    
    def session_exists(self, namespace: str) -> bool:
        """Check if a session file exists for the namespace"""
        return self.get_session_file(namespace).exists()
    
    def list_sessions(self) -> List[str]:
        """List all available session namespaces"""
        sessions = []
        for path in self.sessions_dir.glob("*.session"):
            sessions.append(path.stem)
        return sorted(sessions)
    
    def delete_session(self, namespace: str) -> bool:
        """Delete a session file"""
        session_file = self.get_session_file(namespace)
        if session_file.exists():
            session_file.unlink()
            
            # Also delete .session-journal if exists
            journal_file = self.sessions_dir / f"{namespace}.session-journal"
            if journal_file.exists():
                journal_file.unlink()
            
            return True
        return False
    
    def backup_session(self, namespace: str) -> Optional[Path]:
        """Backup a session file"""
        session_file = self.get_session_file(namespace)
        if session_file.exists():
            backup_path = self.sessions_dir / f"{namespace}.session.backup"
            shutil.copy2(session_file, backup_path)
            return backup_path
        return None
    
    def restore_session(self, namespace: str) -> bool:
        """Restore a session from backup"""
        backup_path = self.sessions_dir / f"{namespace}.session.backup"
        if backup_path.exists():
            session_file = self.get_session_file(namespace)
            shutil.copy2(backup_path, session_file)
            return True
        return False


def get_default_session_manager() -> SessionManager:
    """Get session manager with default path"""
    from tgf.data.config import get_config
    config = get_config()
    return SessionManager(config.sessions_dir)
