"""
Media Handler for TGF

Handles media processing, grouped messages (albums), and media type detection.
"""

from typing import Optional, List, Dict, Tuple, Union
from dataclasses import dataclass
from pathlib import Path
import mimetypes

from telethon.tl.types import (
    Message,
    MessageMediaPhoto,
    MessageMediaDocument,
    MessageMediaWebPage,
    DocumentAttributeFilename,
    DocumentAttributeVideo,
    DocumentAttributeAudio,
    DocumentAttributeImageSize,
    DocumentAttributeAnimated,
    DocumentAttributeSticker,
)

from tgf.core.client import TGClient
from tgf.utils.logger import get_logger


@dataclass
class MediaInfo:
    """Information about media in a message"""
    type: str  # photo, video, audio, document, animation, sticker, voice, video_note
    size: int  # size in bytes
    filename: Optional[str] = None
    mime_type: Optional[str] = None
    width: Optional[int] = None
    height: Optional[int] = None
    duration: Optional[int] = None  # for video/audio


class MediaHandler:
    """Handles media processing and grouped messages"""
    
    def __init__(self, client: TGClient):
        self.client = client
        self.logger = get_logger("tgf.media")
    
    def get_media_info(self, message: Message) -> Optional[MediaInfo]:
        """
        Extract media information from a message
        
        Args:
            message: Telegram message
        
        Returns:
            MediaInfo or None if no media
        """
        if not message.media:
            return None
        
        media = message.media
        
        if isinstance(media, MessageMediaPhoto):
            return self._get_photo_info(media)
        elif isinstance(media, MessageMediaDocument):
            return self._get_document_info(media)
        
        return None
    
    def _get_photo_info(self, media: MessageMediaPhoto) -> MediaInfo:
        """Get info for photo media"""
        photo = media.photo
        
        # Get largest photo size
        largest = max(photo.sizes, key=lambda s: getattr(s, 'size', 0) if hasattr(s, 'size') else 0)
        
        size = getattr(largest, 'size', 0)
        width = getattr(largest, 'w', None)
        height = getattr(largest, 'h', None)
        
        return MediaInfo(
            type="photo",
            size=size,
            mime_type="image/jpeg",
            width=width,
            height=height
        )
    
    def _get_document_info(self, media: MessageMediaDocument) -> MediaInfo:
        """Get info for document media"""
        doc = media.document
        
        media_type = "document"
        filename = None
        width = None
        height = None
        duration = None
        
        for attr in doc.attributes:
            if isinstance(attr, DocumentAttributeFilename):
                filename = attr.file_name
            elif isinstance(attr, DocumentAttributeVideo):
                media_type = "video"
                width = attr.w
                height = attr.h
                duration = attr.duration
            elif isinstance(attr, DocumentAttributeAudio):
                if attr.voice:
                    media_type = "voice"
                else:
                    media_type = "audio"
                duration = attr.duration
            elif isinstance(attr, DocumentAttributeImageSize):
                width = attr.w
                height = attr.h
            elif isinstance(attr, DocumentAttributeAnimated):
                media_type = "animation"
            elif isinstance(attr, DocumentAttributeSticker):
                media_type = "sticker"
        
        return MediaInfo(
            type=media_type,
            size=doc.size,
            filename=filename,
            mime_type=doc.mime_type,
            width=width,
            height=height,
            duration=duration
        )
    
    async def group_messages_by_album(
        self,
        messages: List[Message]
    ) -> List[List[Message]]:
        """
        Group messages by album (grouped_id)
        
        Messages with the same grouped_id belong to the same album.
        Messages without grouped_id are returned as single-item lists.
        
        Args:
            messages: List of messages
        
        Returns:
            List of message groups (albums)
        """
        albums: Dict[int, List[Message]] = {}
        singles: List[List[Message]] = []
        
        for msg in messages:
            if msg.grouped_id:
                if msg.grouped_id not in albums:
                    albums[msg.grouped_id] = []
                albums[msg.grouped_id].append(msg)
            else:
                singles.append([msg])
        
        # Combine albums and singles, preserving order by first message ID
        all_groups = list(albums.values()) + singles
        all_groups.sort(key=lambda g: g[0].id)
        
        return all_groups
    
    async def forward_album(
        self,
        messages: List[Message],
        target_chat,
        use_file_reference: bool = True
    ) -> List[Message]:
        """
        Forward an album (group of media messages) together
        
        Args:
            messages: List of messages in the album
            target_chat: Target chat
            use_file_reference: Try using file references first
        
        Returns:
            List of sent messages
        """
        if len(messages) == 1:
            # Single message, not really an album
            from tgf.core.forwarder import MessageForwarder, ForwardMode
            forwarder = MessageForwarder(self.client)
            result = await forwarder.forward_message(messages[0], target_chat)
            if result.success:
                return [await self.client.get_messages(target_chat, ids=[result.target_msg_id])]
            return []
        
        # Collect media and captions
        media_list = []
        caption = None
        entities = None
        
        for msg in messages:
            if msg.media:
                if use_file_reference:
                    media_list.append(self._get_input_media(msg))
                
                # Use caption from first message with text
                if caption is None and msg.text:
                    caption = msg.text
                    entities = msg.entities
        
        # Send as album
        try:
            results = await self.client.client.send_file(
                target_chat,
                file=media_list,
                caption=caption,
                formatting_entities=entities
            )
            
            return results if isinstance(results, list) else [results]
            
        except Exception as e:
            self.logger.warning(f"Album forward failed: {e}")
            
            # Fallback: forward one by one
            from tgf.core.forwarder import MessageForwarder, ForwardMode
            forwarder = MessageForwarder(self.client)
            
            sent = []
            for msg in messages:
                result = await forwarder.forward_message(msg, target_chat)
                if result.success and result.target_msg_id:
                    sent.append(result.target_msg_id)
            
            return sent
    
    def _get_input_media(self, message: Message):
        """Get InputMedia for album sending"""
        media = message.media
        
        if isinstance(media, MessageMediaPhoto):
            return media.photo
        elif isinstance(media, MessageMediaDocument):
            return media.document
        
        return None
    
    async def download_media(
        self,
        message: Message,
        path: Optional[Path] = None
    ) -> Optional[Union[bytes, Path]]:
        """
        Download media from message
        
        Args:
            message: Message with media
            path: Optional path to save file (returns bytes if None)
        
        Returns:
            Bytes or Path depending on path argument
        """
        if not message.media:
            return None
        
        if path:
            return await self.client.download_media(message, file=str(path))
        else:
            return await self.client.download_media(message, file=bytes)
    
    def format_size(self, size: int) -> str:
        """Format file size for display"""
        for unit in ['B', 'KB', 'MB', 'GB']:
            if size < 1024:
                return f"{size:.1f} {unit}"
            size /= 1024
        return f"{size:.1f} TB"
    
    def format_duration(self, seconds: int) -> str:
        """Format duration for display"""
        if seconds < 60:
            return f"{seconds}s"
        elif seconds < 3600:
            return f"{seconds // 60}m {seconds % 60}s"
        else:
            hours = seconds // 3600
            mins = (seconds % 3600) // 60
            return f"{hours}h {mins}m"
