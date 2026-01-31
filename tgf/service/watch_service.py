"""
Watch Service for TGF

Handles scheduled monitoring and incremental message forwarding.
"""

import asyncio
from typing import Optional, Callable, List, Dict, Any
from dataclasses import dataclass, field
from datetime import datetime

from telethon.tl.types import Message

from tgf.core.client import TGClient
from tgf.core.forwarder import MessageForwarder, ForwardMode, ForwardResult
from tgf.data.config import Config, get_config
from tgf.data.database import Database
from tgf.data.models import Rule, State
from tgf.utils.logger import get_logger


@dataclass
class WatchStatus:
    """Status of a watch operation"""
    rule_name: str
    source_chat: str
    target_chat: str
    last_msg_id: int
    total_forwarded: int
    last_sync_at: Optional[datetime]
    next_sync_in: int = 0  # seconds until next sync
    is_running: bool = False


@dataclass
class SyncResult:
    """Result of a sync operation for a rule"""
    rule_name: str
    messages_found: int = 0
    messages_forwarded: int = 0
    messages_failed: int = 0
    new_last_msg_id: int = 0
    error: Optional[str] = None


class WatchService:
    """Service for watching and syncing channels"""
    
    def __init__(
        self,
        config: Optional[Config] = None,
        namespace: str = "default"
    ):
        self.config = config or get_config()
        self.namespace = namespace
        self.logger = get_logger("tgf.watch")
        
        self._client: Optional[TGClient] = None
        self._forwarder: Optional[MessageForwarder] = None
        self._db: Optional[Database] = None
        self._running: bool = False
        self._stop_event: asyncio.Event = asyncio.Event()
    
    async def connect(self) -> bool:
        """Connect to Telegram and database"""
        # Connect to Telegram
        self._client = TGClient(self.config, self.namespace)
        connected = await self._client.connect()
        
        if connected:
            self._forwarder = MessageForwarder(self._client)
        
        # Connect to database
        self._db = Database(self.config.db_path)
        await self._db.connect()
        
        return connected
    
    async def disconnect(self) -> None:
        """Disconnect from Telegram and database"""
        if self._client:
            await self._client.disconnect()
            self._client = None
            self._forwarder = None
        
        if self._db:
            await self._db.close()
            self._db = None
    
    async def sync_rule(
        self,
        rule_name: str,
        on_message: Optional[Callable[[Message], None]] = None
    ) -> SyncResult:
        """
        Sync a single rule - forward new messages since last sync
        
        Args:
            rule_name: Name of the rule to sync
            on_message: Callback for each message processed
        
        Returns:
            SyncResult with statistics
        """
        import random
        
        result = SyncResult(rule_name=rule_name)
        
        # Get rule
        rule_dict = await self._db.get_rule(name=rule_name)
        if not rule_dict:
            result.error = f"Rule not found: {rule_name}"
            return result
        
        rule = Rule.from_dict(rule_dict)
        
        if not rule.enabled:
            result.error = "Rule is disabled"
            return result
        
        # Get state
        state_dict = await self._db.get_state(rule.id, self.namespace)
        last_msg_id = state_dict["last_msg_id"] if state_dict else 0
        
        self.logger.info(f"Syncing rule '{rule_name}': last_msg_id={last_msg_id}")
        
        try:
            # Get entities
            source = await self._client.get_entity(rule.source_chat)
            target = await self._client.get_entity(rule.target_chat)
            
            # First time sync: Initialize to latest message, don't forward old messages
            if last_msg_id == 0:
                self.logger.info(f"First sync for rule '{rule_name}', initializing to latest message")
                
                # Get the latest message from source
                async for msg in self._client.iter_messages(source, limit=1):
                    last_msg_id = msg.id
                    self.logger.info(f"Initialized last_msg_id to {last_msg_id}")
                    
                    # Save the initial state
                    await self._db.update_state(
                        rule_id=rule.id,
                        namespace=self.namespace,
                        last_msg_id=last_msg_id,
                        increment_forwarded=0
                    )
                    break
                
                # Return empty result - no messages to forward on first sync
                self.logger.info(f"Rule '{rule_name}' initialized. Waiting for new messages.")
                return result
            
            # Get new messages (> last_msg_id)
            messages = []
            async for msg in self._client.iter_messages(
                source,
                min_id=last_msg_id,
                reverse=True  # Oldest first
            ):
                messages.append(msg)
            
            result.messages_found = len(messages)
            
            if not messages:
                self.logger.info(f"No new messages for rule '{rule_name}'")
                return result
            
            # Forward messages with random delay
            mode = ForwardMode(rule.mode)
            
            for i, msg in enumerate(messages):
                if on_message:
                    on_message(msg)
                
                forward_result = await self._forwarder.forward_message(
                    msg, target, mode=mode
                )
                
                if forward_result.success:
                    result.messages_forwarded += 1
                else:
                    result.messages_failed += 1
                    self.logger.warning(
                        f"Failed to forward message {msg.id}: {forward_result.error}"
                    )
                
                result.new_last_msg_id = max(result.new_last_msg_id, msg.id)
                
                # Random delay between messages (5-10 seconds) to avoid rate limiting
                if i < len(messages) - 1:  # Don't delay after last message
                    delay = random.uniform(5.0, 10.0)
                    self.logger.debug(f"Waiting {delay:.1f}s before next message")
                    await asyncio.sleep(delay)
            
            # Update state
            if result.new_last_msg_id > 0:
                await self._db.update_state(
                    rule_id=rule.id,
                    namespace=self.namespace,
                    last_msg_id=result.new_last_msg_id,
                    increment_forwarded=result.messages_forwarded
                )
            
            self.logger.info(
                f"Synced rule '{rule_name}': found={result.messages_found}, "
                f"forwarded={result.messages_forwarded}, failed={result.messages_failed}"
            )
            
            return result
            
        except Exception as e:
            result.error = str(e)
            self.logger.error(f"Sync failed for rule '{rule_name}': {e}")
            return result
    
    async def sync_all(
        self,
        on_rule_start: Optional[Callable[[str], None]] = None,
        on_rule_complete: Optional[Callable[[SyncResult], None]] = None
    ) -> List[SyncResult]:
        """
        Sync all enabled rules
        
        Args:
            on_rule_start: Callback when starting a rule
            on_rule_complete: Callback when rule completes
        
        Returns:
            List of SyncResults for all rules
        """
        results = []
        
        # Get all enabled rules
        rules = await self._db.get_all_rules(enabled_only=True)
        
        for rule_dict in rules:
            rule = Rule.from_dict(rule_dict)
            
            if on_rule_start:
                on_rule_start(rule.name)
            
            result = await self.sync_rule(rule.name)
            results.append(result)
            
            if on_rule_complete:
                on_rule_complete(result)
        
        return results
    
    async def watch(
        self,
        rule_name: Optional[str] = None,
        on_sync: Optional[Callable[[List[SyncResult]], None]] = None
    ) -> None:
        """
        Start watching and syncing rules periodically
        
        Args:
            rule_name: If specified, only watch this rule
            on_sync: Callback after each sync cycle
        """
        self._running = True
        self._stop_event.clear()
        
        self.logger.info("Starting watch mode...")
        
        try:
            while self._running:
                if rule_name:
                    # Watch single rule
                    rule_dict = await self._db.get_rule(name=rule_name)
                    if rule_dict:
                        rule = Rule.from_dict(rule_dict)
                        result = await self.sync_rule(rule_name)
                        if on_sync:
                            on_sync([result])
                        
                        interval = rule.interval_min * 60
                    else:
                        self.logger.error(f"Rule not found: {rule_name}")
                        break
                else:
                    # Watch all rules
                    results = await self.sync_all()
                    if on_sync:
                        on_sync(results)
                    
                    # Use minimum interval from all rules
                    rules = await self._db.get_all_rules(enabled_only=True)
                    intervals = [r["interval_min"] for r in rules]
                    interval = min(intervals) * 60 if intervals else 1800  # Default 30 min
                
                # Wait for next sync or stop signal
                self.logger.info(f"Next sync in {interval}s")
                
                try:
                    await asyncio.wait_for(
                        self._stop_event.wait(),
                        timeout=interval
                    )
                    # Stop event was set
                    break
                except asyncio.TimeoutError:
                    # Timeout, continue with next sync
                    pass
                    
        finally:
            self._running = False
            self.logger.info("Watch mode stopped")
    
    def stop(self) -> None:
        """Stop watching"""
        self._running = False
        self._stop_event.set()
    
    async def get_status(self, rule_name: Optional[str] = None) -> List[WatchStatus]:
        """
        Get status of rules
        
        Args:
            rule_name: If specified, get status for this rule only
        
        Returns:
            List of WatchStatus
        """
        statuses = []
        
        if rule_name:
            rule_dict = await self._db.get_rule(name=rule_name)
            rules = [rule_dict] if rule_dict else []
        else:
            rules = await self._db.get_all_rules()
        
        for rule_dict in rules:
            rule = Rule.from_dict(rule_dict)
            state_dict = await self._db.get_state(rule.id, self.namespace)
            state = State.from_dict(state_dict) if state_dict else None
            
            status = WatchStatus(
                rule_name=rule.name,
                source_chat=rule.source_chat,
                target_chat=rule.target_chat,
                last_msg_id=state.last_msg_id if state else 0,
                total_forwarded=state.total_forwarded if state else 0,
                last_sync_at=state.last_sync_at if state else None,
                is_running=self._running
            )
            
            statuses.append(status)
        
        return statuses
    
    async def __aenter__(self):
        await self.connect()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        self.stop()
        await self.disconnect()
