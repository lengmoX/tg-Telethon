"""
Message Forwarder for TGF

Handles message forwarding with clone and direct modes.
"""

from typing import Optional, Union, List, Tuple
from dataclasses import dataclass
from enum import Enum

from telethon.tl.types import (
    Message,
    MessageMediaPhoto,
    MessageMediaDocument,
    MessageMediaWebPage,
    DocumentAttributeFilename,
    DocumentAttributeVideo,
    DocumentAttributeAudio,
    InputMediaPhoto,
    InputMediaDocument,
)
from telethon.errors import (
    ChatForwardsRestrictedError,
    MediaCaptionTooLongError,
    FloodWaitError,
)

from tgf.core.client import TGClient
from tgf.utils.logger import get_logger
from tgf.utils.exceptions import ForwardError, RestrictedChannelError


class ForwardMode(str, Enum):
    """Forwarding mode"""
    CLONE = "clone"    # Copy message without forward header
    DIRECT = "direct"  # Native forward with header


@dataclass
class ForwardResult:
    """Result of a forward operation"""
    success: bool
    source_msg_id: int
    target_msg_id: Optional[int] = None
    mode_used: Optional[ForwardMode] = None
    error: Optional[str] = None
    downloaded: bool = False  # True if media was downloaded/uploaded


class MessageForwarder:
    """
    Forwards messages between Telegram chats.
    
    Supports two modes:
    - clone: Copy message using send_message/send_file (no forward header)
    - direct: Native forward_messages (with "Forwarded from" header)
    """
    
    def __init__(self, client: TGClient):
        self.client = client
        self.logger = get_logger("tgf.forwarder")
    
    async def forward_message(
        self,
        message: Message,
        target_chat,
        mode: ForwardMode = ForwardMode.CLONE,
        fallback_to_download: bool = True
    ) -> ForwardResult:
        """
        Forward a single message
        
        Args:
            message: Source message to forward
            target_chat: Target chat entity
            mode: Forwarding mode
            fallback_to_download: If clone fails, download and re-upload
        
        Returns:
            ForwardResult with success status and details
        """
        source_msg_id = message.id
        
        try:
            if mode == ForwardMode.DIRECT:
                result = await self._forward_direct(message, target_chat)
            else:
                result = await self._forward_clone(message, target_chat, fallback_to_download)
            
            return result
            
        except FloodWaitError as e:
            self.logger.warning(f"Rate limited. Need to wait {e.seconds}s")
            raise
            
        except Exception as e:
            self.logger.error(f"Forward failed for message {source_msg_id}: {e}")
            return ForwardResult(
                success=False,
                source_msg_id=source_msg_id,
                error=str(e)
            )
    
    async def _forward_direct(
        self,
        message: Message,
        target_chat
    ) -> ForwardResult:
        """Forward using native forward API (with header)"""
        source_msg_id = message.id
        source_chat = message.chat
        
        try:
            result = await self.client.forward_messages(
                target_chat,
                message.id,
                source_chat
            )
            
            # Result could be a list or single message
            target_msg_id = result.id if hasattr(result, 'id') else result[0].id if result else None
            
            return ForwardResult(
                success=True,
                source_msg_id=source_msg_id,
                target_msg_id=target_msg_id,
                mode_used=ForwardMode.DIRECT
            )
            
        except ChatForwardsRestrictedError:
            raise RestrictedChannelError(
                f"Channel restricts forwarding. Use clone mode with download."
            )
    
    async def _forward_clone(
        self,
        message: Message,
        target_chat,
        fallback_to_download: bool = True
    ) -> ForwardResult:
        """Forward by copying message content (no header)"""
        source_msg_id = message.id
        
        # Check if message has media
        if message.media:
            return await self._clone_media_message(
                message, target_chat, fallback_to_download
            )
        else:
            return await self._clone_text_message(message, target_chat)
    
    async def _clone_text_message(
        self,
        message: Message,
        target_chat
    ) -> ForwardResult:
        """Clone a text-only message"""
        source_msg_id = message.id
        
        if not message.text:
            return ForwardResult(
                success=False,
                source_msg_id=source_msg_id,
                error="Empty message"
            )
        
        result = await self.client.send_message(
            target_chat,
            message.text,
            formatting_entities=message.entities,
            link_preview=bool(message.media and isinstance(message.media, MessageMediaWebPage))
        )
        
        return ForwardResult(
            success=True,
            source_msg_id=source_msg_id,
            target_msg_id=result.id,
            mode_used=ForwardMode.CLONE
        )
    
    async def _clone_media_message(
        self,
        message: Message,
        target_chat,
        fallback_to_download: bool = True
    ) -> ForwardResult:
        """Clone a message with media"""
        source_msg_id = message.id
        
        # Try to send using file reference (fast, no download)
        try:
            result = await self._send_with_file_reference(message, target_chat)
            return ForwardResult(
                success=True,
                source_msg_id=source_msg_id,
                target_msg_id=result.id,
                mode_used=ForwardMode.CLONE,
                downloaded=False
            )
            
        except (Exception,) as e:
            if not fallback_to_download:
                return ForwardResult(
                    success=False,
                    source_msg_id=source_msg_id,
                    error=f"File reference failed: {e}"
                )
            
            self.logger.debug(f"File reference failed, downloading: {e}")
        
        # Fallback: download and re-upload
        return await self._download_and_upload(message, target_chat)
    
    async def _send_with_file_reference(
        self,
        message: Message,
        target_chat
    ) -> Message:
        """
        Send media using file reference (no download needed).
        This works if the file is still cached on Telegram's servers.
        """
        media = message.media
        caption = message.text or ""
        entities = message.entities
        
        if isinstance(media, MessageMediaPhoto):
            # Photo
            return await self.client.send_file(
                target_chat,
                file=media.photo,
                caption=caption,
                formatting_entities=entities
            )
            
        elif isinstance(media, MessageMediaDocument):
            # Document (video, file, audio, gif, etc.)
            return await self.client.send_file(
                target_chat,
                file=media.document,
                caption=caption,
                formatting_entities=entities
            )
        else:
            raise ForwardError(f"Unsupported media type: {type(media).__name__}")
    
    async def _download_and_upload(
        self,
        message: Message,
        target_chat
    ) -> ForwardResult:
        """Download media and re-upload to target"""
        source_msg_id = message.id
        
        try:
            # Download to bytes
            file_bytes = await self.client.download_media(message, file=bytes)
            
            if not file_bytes:
                return ForwardResult(
                    success=False,
                    source_msg_id=source_msg_id,
                    error="Failed to download media"
                )
            
            # Determine file attributes
            file_name = self._get_media_filename(message)
            caption = message.text or ""
            entities = message.entities
            
            # Re-upload
            result = await self.client.send_file(
                target_chat,
                file=file_bytes,
                caption=caption,
                formatting_entities=entities,
                file_name=file_name,
                force_document=self._is_document(message.media)
            )
            
            return ForwardResult(
                success=True,
                source_msg_id=source_msg_id,
                target_msg_id=result.id,
                mode_used=ForwardMode.CLONE,
                downloaded=True
            )
            
        except Exception as e:
            return ForwardResult(
                success=False,
                source_msg_id=source_msg_id,
                error=f"Download/upload failed: {e}"
            )
    
    def _get_media_filename(self, message: Message) -> Optional[str]:
        """Extract filename from message media"""
        if not message.media:
            return None
        
        if isinstance(message.media, MessageMediaDocument):
            doc = message.media.document
            for attr in doc.attributes:
                if isinstance(attr, DocumentAttributeFilename):
                    return attr.file_name
        
        return None
    
    def _is_document(self, media) -> bool:
        """Check if media should be sent as document"""
        if isinstance(media, MessageMediaDocument):
            doc = media.document
            for attr in doc.attributes:
                if isinstance(attr, (DocumentAttributeVideo, DocumentAttributeAudio)):
                    return False
            return True
        return False
    
    async def forward_messages(
        self,
        messages: List[Message],
        target_chat,
        mode: ForwardMode = ForwardMode.CLONE,
        fallback_to_download: bool = True
    ) -> List[ForwardResult]:
        """
        Forward multiple messages
        
        Args:
            messages: List of messages to forward
            target_chat: Target chat entity
            mode: Forwarding mode
            fallback_to_download: If clone fails, download and re-upload
        
        Returns:
            List of ForwardResult for each message
        """
        results = []
        
        for message in messages:
            result = await self.forward_message(
                message, target_chat, mode, fallback_to_download
            )
            results.append(result)
        
        return results
    
    @staticmethod
    def can_forward_direct(message: Message) -> bool:
        """Check if message can be forwarded with direct mode"""
        # Check if channel restricts forwarding
        chat = message.chat
        if hasattr(chat, 'noforwards') and chat.noforwards:
            return False
        return True
