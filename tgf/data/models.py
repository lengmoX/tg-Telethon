"""
Data Models for TGF

Dataclass-based models for rules and state.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional


@dataclass
class Rule:
    """Forwarding rule model"""
    
    id: Optional[int] = None
    name: str = ""
    source_chat: str = ""
    target_chat: str = ""
    mode: str = "clone"  # clone or direct
    interval_min: int = 30
    enabled: bool = True
    note: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    
    @classmethod
    def from_dict(cls, data: dict) -> "Rule":
        """Create Rule from database row dict"""
        return cls(
            id=data.get("id"),
            name=data.get("name", ""),
            source_chat=data.get("source_chat", ""),
            target_chat=data.get("target_chat", ""),
            mode=data.get("mode", "clone"),
            interval_min=data.get("interval_min", 30),
            enabled=bool(data.get("enabled", True)),
            note=data.get("note"),
            created_at=_parse_datetime(data.get("created_at")),
            updated_at=_parse_datetime(data.get("updated_at")),
        )
    
    def to_dict(self) -> dict:
        """Convert to dict for database operations"""
        return {
            "name": self.name,
            "source_chat": self.source_chat,
            "target_chat": self.target_chat,
            "mode": self.mode,
            "interval_min": self.interval_min,
            "enabled": self.enabled,
            "note": self.note,
        }


@dataclass
class State:
    """Sync state model"""
    
    id: Optional[int] = None
    rule_id: int = 0
    namespace: str = "default"
    last_msg_id: int = 0
    last_sync_at: Optional[datetime] = None
    total_forwarded: int = 0
    note: Optional[str] = None
    
    # Joined fields from rules table
    rule_name: Optional[str] = None
    source_chat: Optional[str] = None
    target_chat: Optional[str] = None
    
    @classmethod
    def from_dict(cls, data: dict) -> "State":
        """Create State from database row dict"""
        return cls(
            id=data.get("id"),
            rule_id=data.get("rule_id", 0),
            namespace=data.get("namespace", "default"),
            last_msg_id=data.get("last_msg_id", 0),
            last_sync_at=_parse_datetime(data.get("last_sync_at")),
            total_forwarded=data.get("total_forwarded", 0),
            note=data.get("note"),
            rule_name=data.get("rule_name"),
            source_chat=data.get("source_chat"),
            target_chat=data.get("target_chat"),
        )


def _parse_datetime(value) -> Optional[datetime]:
    """Parse datetime from string or return None"""
    if value is None:
        return None
    if isinstance(value, datetime):
        return value
    try:
        return datetime.fromisoformat(value)
    except (ValueError, TypeError):
        return None
