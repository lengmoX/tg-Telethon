"""
Database Management for TGF

SQLite database with aiosqlite for async operations.
"""

import sqlite3
import aiosqlite
from pathlib import Path
from typing import Optional, List, Dict, Any
from contextlib import asynccontextmanager
from datetime import datetime


class Database:
    """SQLite database manager for TGF"""
    
    SCHEMA_VERSION = 1
    
    def __init__(self, db_path: Path):
        self.db_path = db_path
        self._connection: Optional[aiosqlite.Connection] = None
    
    async def connect(self) -> None:
        """Connect to database and initialize schema"""
        self._connection = await aiosqlite.connect(self.db_path)
        self._connection.row_factory = aiosqlite.Row
        await self._init_schema()
    
    async def close(self) -> None:
        """Close database connection"""
        if self._connection:
            await self._connection.close()
            self._connection = None
    
    @asynccontextmanager
    async def get_connection(self):
        """Get database connection as context manager"""
        if not self._connection:
            await self.connect()
        yield self._connection
    
    async def _init_schema(self) -> None:
        """Initialize database schema"""
        async with self._connection.cursor() as cursor:
            # Create rules table
            await cursor.execute("""
                CREATE TABLE IF NOT EXISTS rules (
                    id              INTEGER PRIMARY KEY AUTOINCREMENT,
                    name            TEXT NOT NULL UNIQUE,
                    source_chat     TEXT NOT NULL,
                    target_chat     TEXT NOT NULL,
                    mode            TEXT DEFAULT 'clone',
                    interval_min    INTEGER DEFAULT 30,
                    enabled         INTEGER DEFAULT 1,
                    note            TEXT,
                    created_at      TEXT DEFAULT CURRENT_TIMESTAMP,
                    updated_at      TEXT DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Create state table
            await cursor.execute("""
                CREATE TABLE IF NOT EXISTS state (
                    id              INTEGER PRIMARY KEY AUTOINCREMENT,
                    rule_id         INTEGER NOT NULL,
                    namespace       TEXT NOT NULL DEFAULT 'default',
                    last_msg_id     INTEGER DEFAULT 0,
                    last_sync_at    TEXT,
                    total_forwarded INTEGER DEFAULT 0,
                    note            TEXT,
                    UNIQUE(rule_id, namespace),
                    FOREIGN KEY (rule_id) REFERENCES rules(id) ON DELETE CASCADE
                )
            """)
            
            # Create indexes
            await cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_rules_enabled ON rules(enabled)
            """)
            await cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_state_rule_ns ON state(rule_id, namespace)
            """)
            
            # Create schema version table
            await cursor.execute("""
                CREATE TABLE IF NOT EXISTS schema_info (
                    key     TEXT PRIMARY KEY,
                    value   TEXT
                )
            """)
            
            # Set schema version
            await cursor.execute("""
                INSERT OR REPLACE INTO schema_info (key, value)
                VALUES ('version', ?)
            """, (str(self.SCHEMA_VERSION),))
            
            await self._connection.commit()
    
    # ============ Rule CRUD Operations ============
    
    async def create_rule(
        self,
        name: str,
        source_chat: str,
        target_chat: str,
        mode: str = "clone",
        interval_min: int = 30,
        enabled: bool = True,
        note: Optional[str] = None
    ) -> int:
        """Create a new forwarding rule"""
        async with self._connection.cursor() as cursor:
            await cursor.execute("""
                INSERT INTO rules (name, source_chat, target_chat, mode, interval_min, enabled, note)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (name, source_chat, target_chat, mode, interval_min, int(enabled), note))
            await self._connection.commit()
            return cursor.lastrowid
    
    async def get_rule(self, rule_id: Optional[int] = None, name: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """Get a rule by ID or name"""
        async with self._connection.cursor() as cursor:
            if rule_id:
                await cursor.execute("SELECT * FROM rules WHERE id = ?", (rule_id,))
            elif name:
                await cursor.execute("SELECT * FROM rules WHERE name = ?", (name,))
            else:
                return None
            
            row = await cursor.fetchone()
            return dict(row) if row else None
    
    async def get_all_rules(self, enabled_only: bool = False) -> List[Dict[str, Any]]:
        """Get all rules"""
        async with self._connection.cursor() as cursor:
            if enabled_only:
                await cursor.execute("SELECT * FROM rules WHERE enabled = 1 ORDER BY id")
            else:
                await cursor.execute("SELECT * FROM rules ORDER BY id")
            
            rows = await cursor.fetchall()
            return [dict(row) for row in rows]
    
    async def update_rule(self, rule_id: int, **kwargs) -> bool:
        """Update a rule"""
        if not kwargs:
            return False
        
        # Build SET clause dynamically
        set_parts = []
        values = []
        
        allowed_fields = {"name", "source_chat", "target_chat", "mode", "interval_min", "enabled", "note"}
        for key, value in kwargs.items():
            if key in allowed_fields:
                set_parts.append(f"{key} = ?")
                if key == "enabled":
                    values.append(int(value))
                else:
                    values.append(value)
        
        if not set_parts:
            return False
        
        set_parts.append("updated_at = ?")
        values.append(datetime.now().isoformat())
        values.append(rule_id)
        
        query = f"UPDATE rules SET {', '.join(set_parts)} WHERE id = ?"
        
        async with self._connection.cursor() as cursor:
            await cursor.execute(query, values)
            await self._connection.commit()
            return cursor.rowcount > 0
    
    async def delete_rule(self, rule_id: Optional[int] = None, name: Optional[str] = None) -> bool:
        """Delete a rule by ID or name"""
        async with self._connection.cursor() as cursor:
            if rule_id:
                await cursor.execute("DELETE FROM rules WHERE id = ?", (rule_id,))
            elif name:
                await cursor.execute("DELETE FROM rules WHERE name = ?", (name,))
            else:
                return False
            
            await self._connection.commit()
            return cursor.rowcount > 0
    
    # ============ State CRUD Operations ============
    
    async def get_state(self, rule_id: int, namespace: str = "default") -> Optional[Dict[str, Any]]:
        """Get state for a rule and namespace"""
        async with self._connection.cursor() as cursor:
            await cursor.execute("""
                SELECT * FROM state WHERE rule_id = ? AND namespace = ?
            """, (rule_id, namespace))
            
            row = await cursor.fetchone()
            return dict(row) if row else None
    
    async def update_state(
        self,
        rule_id: int,
        namespace: str = "default",
        last_msg_id: Optional[int] = None,
        increment_forwarded: int = 0,
        note: Optional[str] = None
    ) -> None:
        """Update or create state for a rule"""
        async with self._connection.cursor() as cursor:
            # Check if state exists
            await cursor.execute("""
                SELECT id, total_forwarded FROM state WHERE rule_id = ? AND namespace = ?
            """, (rule_id, namespace))
            
            row = await cursor.fetchone()
            
            if row:
                # Update existing state
                updates = ["last_sync_at = ?"]
                values = [datetime.now().isoformat()]
                
                if last_msg_id is not None:
                    updates.append("last_msg_id = ?")
                    values.append(last_msg_id)
                
                if increment_forwarded > 0:
                    updates.append("total_forwarded = ?")
                    values.append(row["total_forwarded"] + increment_forwarded)
                
                if note is not None:
                    updates.append("note = ?")
                    values.append(note)
                
                values.append(row["id"])
                
                await cursor.execute(
                    f"UPDATE state SET {', '.join(updates)} WHERE id = ?",
                    values
                )
            else:
                # Create new state
                await cursor.execute("""
                    INSERT INTO state (rule_id, namespace, last_msg_id, last_sync_at, total_forwarded, note)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, (
                    rule_id,
                    namespace,
                    last_msg_id or 0,
                    datetime.now().isoformat(),
                    increment_forwarded,
                    note
                ))
            
            await self._connection.commit()
    
    async def get_all_states(self, namespace: str = "default") -> List[Dict[str, Any]]:
        """Get all states for a namespace"""
        async with self._connection.cursor() as cursor:
            await cursor.execute("""
                SELECT s.*, r.name as rule_name, r.source_chat, r.target_chat
                FROM state s
                JOIN rules r ON s.rule_id = r.id
                WHERE s.namespace = ?
                ORDER BY s.rule_id
            """, (namespace,))
            
            rows = await cursor.fetchall()
            return [dict(row) for row in rows]


# Synchronous wrapper for simple operations
class SyncDatabase:
    """Synchronous database wrapper for CLI operations"""
    
    def __init__(self, db_path: Path):
        self.db_path = db_path
    
    def _get_connection(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn
    
    def get_all_rules(self, enabled_only: bool = False) -> List[Dict[str, Any]]:
        """Get all rules synchronously"""
        conn = self._get_connection()
        try:
            if enabled_only:
                rows = conn.execute("SELECT * FROM rules WHERE enabled = 1 ORDER BY id").fetchall()
            else:
                rows = conn.execute("SELECT * FROM rules ORDER BY id").fetchall()
            return [dict(row) for row in rows]
        finally:
            conn.close()
    
    def get_rule(self, name: str) -> Optional[Dict[str, Any]]:
        """Get a rule by name synchronously"""
        conn = self._get_connection()
        try:
            row = conn.execute("SELECT * FROM rules WHERE name = ?", (name,)).fetchone()
            return dict(row) if row else None
        finally:
            conn.close()
