"""
Forward Service for TGF

Handles manual forwarding with progress tracking and error handling.
"""

import asyncio
from typing import Optional, Callable, List, AsyncIterator
from dataclasses import dataclass, field
from datetime import datetime

from telethon.tl.types import Message
from telethon.errors import FloodWaitError

from tgf.core.client import TGClient
from tgf.core.forwarder import MessageForwarder, ForwardMode, ForwardResult
from tgf.core.media import MediaHandler
from tgf.data.config import Config, get_config
from tgf.data.database import Database
from tgf.utils.logger import get_logger
from tgf.utils.retry import RetryContext


@dataclass
class ForwardProgress:
    """Progress information for forwarding"""
    total: int = 0
    processed: int = 0
    success: int = 0
    failed: int = 0
    skipped: int = 0
    current_msg_id: int = 0
    started_at: datetime = field(default_factory=datetime.now)
    
    @property
    def percentage(self) -> float:
        if self.total == 0:
            return 0.0
        return (self.processed / self.total) * 100
    
    @property
    def elapsed_seconds(self) -> float:
        return (datetime.now() - self.started_at).total_seconds()


@dataclass
class ForwardOptions:
    """Options for forward operation"""
    mode: ForwardMode = ForwardMode.CLONE
    limit: Optional[int] = None
    from_id: int = 0  # min_id: forward messages > from_id
    to_id: int = 0    # max_id: forward messages < to_id
    dry_run: bool = False
    fallback_to_download: bool = True


class ForwardService:
    """Service for manual message forwarding"""
    
    def __init__(
        self,
        config: Optional[Config] = None,
        namespace: str = "default"
    ):
        self.config = config or get_config()
        self.namespace = namespace
        self.logger = get_logger("tgf.forward")
        
        self._client: Optional[TGClient] = None
        self._forwarder: Optional[MessageForwarder] = None
        self._media_handler: Optional[MediaHandler] = None
    
    async def connect(self) -> bool:
        """Connect to Telegram"""
        self._client = TGClient(self.config, self.namespace)
        connected = await self._client.connect()
        
        if connected:
            self._forwarder = MessageForwarder(self._client)
            self._media_handler = MediaHandler(self._client)
        
        return connected
    
    async def disconnect(self) -> None:
        """Disconnect from Telegram"""
        if self._client:
            await self._client.disconnect()
            self._client = None
            self._forwarder = None
            self._media_handler = None
    
    async def forward(
        self,
        source_chat: str,
        target_chat: str,
        options: Optional[ForwardOptions] = None,
        on_progress: Optional[Callable[[ForwardProgress], None]] = None
    ) -> ForwardProgress:
        """
        Forward messages from source to target
        
        Args:
            source_chat: Source chat (username/ID/link)
            target_chat: Target chat
            options: Forwarding options
            on_progress: Progress callback
        
        Returns:
            Final progress with statistics
        """
        options = options or ForwardOptions()
        progress = ForwardProgress()
        
        try:
            # Get entities
            source = await self._client.get_entity(source_chat)
            target = await self._client.get_entity(target_chat)
            
            self.logger.info(f"Forwarding from {source_chat} to {target_chat}")
            
            # Get messages
            messages = await self._get_messages(source, options)
            progress.total = len(messages)
            
            if on_progress:
                on_progress(progress)
            
            # Forward each message
            for msg in messages:
                progress.current_msg_id = msg.id
                
                if options.dry_run:
                    self.logger.debug(f"[DRY RUN] Would forward message {msg.id}")
                    progress.skipped += 1
                else:
                    result = await self._forward_with_retry(
                        msg, target, options
                    )
                    
                    if result.success:
                        progress.success += 1
                    else:
                        progress.failed += 1
                        self.logger.warning(f"Failed to forward {msg.id}: {result.error}")
                
                progress.processed += 1
                
                if on_progress:
                    on_progress(progress)
            
            return progress
            
        except Exception as e:
            self.logger.error(f"Forward failed: {e}")
            raise
    
    async def _get_messages(
        self,
        source,
        options: ForwardOptions
    ) -> List[Message]:
        """Get messages from source based on options"""
        messages = []
        
        kwargs = {}
        if options.from_id > 0:
            kwargs['min_id'] = options.from_id
        if options.to_id > 0:
            kwargs['max_id'] = options.to_id
        if options.limit:
            kwargs['limit'] = options.limit
        
        # Get messages in reverse order (oldest first)
        async for msg in self._client.iter_messages(source, reverse=True, **kwargs):
            messages.append(msg)
            
            if options.limit and len(messages) >= options.limit:
                break
        
        return messages
    
    async def _forward_with_retry(
        self,
        message: Message,
        target,
        options: ForwardOptions
    ) -> ForwardResult:
        """Forward message with retry on failure"""
        retry = RetryContext(
            max_retries=self.config.max_retries,
            min_delay=self.config.retry_min_delay,
            max_delay=self.config.retry_max_delay
        )
        
        last_result = None
        
        for attempt in retry:
            try:
                result = await self._forwarder.forward_message(
                    message,
                    target,
                    mode=options.mode,
                    fallback_to_download=options.fallback_to_download
                )
                
                if result.success:
                    retry.success()
                    return result
                
                last_result = result
                
                # Check if we should retry
                if result.error and "restricted" in result.error.lower():
                    # Don't retry for restricted channels
                    break
                
                if not await retry.handle_error(Exception(result.error or "Unknown error")):
                    break
                    
            except FloodWaitError as e:
                self.logger.warning(f"Flood wait: {e.seconds}s")
                await asyncio.sleep(e.seconds)
                # Don't count as a retry attempt
                retry.attempt -= 1
                
            except Exception as e:
                if not await retry.handle_error(e):
                    break
        
        return last_result or ForwardResult(
            success=False,
            source_msg_id=message.id,
            error="Max retries exceeded"
        )
    
    async def preview_messages(
        self,
        source_chat: str,
        limit: int = 10,
        from_id: int = 0
    ) -> List[dict]:
        """
        Preview messages without forwarding
        
        Returns:
            List of message info dicts
        """
        source = await self._client.get_entity(source_chat)
        
        messages = []
        async for msg in self._client.iter_messages(source, limit=limit, min_id=from_id):
            info = {
                "id": msg.id,
                "date": msg.date.isoformat() if msg.date else None,
                "text": msg.text[:100] + "..." if msg.text and len(msg.text) > 100 else msg.text,
                "has_media": bool(msg.media),
            }
            
            if msg.media:
                media_info = self._media_handler.get_media_info(msg)
                if media_info:
                    info["media_type"] = media_info.type
                    info["media_size"] = self._media_handler.format_size(media_info.size)
            
            messages.append(info)
        
        return messages
    
    async def __aenter__(self):
        await self.connect()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.disconnect()
