"""
Message Forwarder for TGF

Handles message forwarding with clone and direct modes.
Supports streaming download/upload for restricted channels.
"""

import os
import tempfile
from typing import Optional, List, Callable
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
    DocumentAttributeAnimated,
    DocumentAttributeSticker,
    MessageEntityBold,
    MessageEntityItalic,
    MessageEntityCode,
    MessageEntityPre,
    MessageEntityTextUrl,
    MessageEntityMentionName,
    MessageEntityHashtag,
    MessageEntityCashtag,
    MessageEntityMention,
    MessageEntityUrl,
    MessageEntityEmail,
    MessageEntityPhone,
    MessageEntityUnderline,
    MessageEntityStrike,
    MessageEntitySpoiler,
)
from telethon.errors import (
    ChatForwardsRestrictedError,
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


# Progress callback type: (current_bytes, total_bytes) -> None
ProgressCallback = Callable[[int, int], None]


def filter_entities(entities, text: str):
    """
    Filter and clean message entities for safe forwarding.
    
    Issues addressed:
    - Bold/italic entities that overlap with hashtags/mentions cause ** to appear
    - Some entity offsets may be incorrect after text processing
    
    Returns:
        Filtered list of entities or None if entities should be ignored
    """
    if not entities:
        return None
    
    # Types that should always be preserved
    safe_types = (
        MessageEntityUrl,
        MessageEntityEmail,
        MessageEntityPhone,
        MessageEntityTextUrl,
        MessageEntityMentionName,
    )
    
    # Types that Telegram auto-generates (don't need to send explicitly)
    auto_types = (
        MessageEntityHashtag,
        MessageEntityCashtag,
        MessageEntityMention,
    )
    
    # Formatting types that might cause issues
    format_types = (
        MessageEntityBold,
        MessageEntityItalic,
        MessageEntityUnderline,
        MessageEntityStrike,
        MessageEntityCode,
        MessageEntityPre,
        MessageEntitySpoiler,
    )
    
    filtered = []
    
    for entity in entities:
        # Skip auto-generated types - Telegram will recreate them
        if isinstance(entity, auto_types):
            continue
        
        # Always keep safe types
        if isinstance(entity, safe_types):
            filtered.append(entity)
            continue
        
        # For formatting types, check if they overlap with auto-generated content
        if isinstance(entity, format_types):
            start = entity.offset
            end = entity.offset + entity.length
            segment = text[start:end] if end <= len(text) else ""
            
            # Skip if segment starts with # or @ (likely hashtag/mention)
            if segment.startswith('#') or segment.startswith('@') or segment.startswith('$'):
                continue
            
            filtered.append(entity)
            continue
        
        # Keep other entity types
        filtered.append(entity)
    
    return filtered if filtered else None


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
        fallback_to_download: bool = True,
        progress_callback: Optional[ProgressCallback] = None
    ) -> ForwardResult:
        """
        Forward a single message
        
        Args:
            message: Source message to forward
            target_chat: Target chat entity
            mode: Forwarding mode
            fallback_to_download: If clone fails, download and re-upload
            progress_callback: Callback for download/upload progress
        
        Returns:
            ForwardResult with success status and details
        """
        source_msg_id = message.id
        
        try:
            if mode == ForwardMode.DIRECT:
                result = await self._forward_direct(message, target_chat)
            else:
                result = await self._forward_clone(
                    message, target_chat, fallback_to_download, progress_callback
                )
            
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
        fallback_to_download: bool = True,
        progress_callback: Optional[ProgressCallback] = None
    ) -> ForwardResult:
        """Forward by copying message content (no header)"""
        source_msg_id = message.id
        
        # Check if message has media
        if message.media:
            return await self._clone_media_message(
                message, target_chat, fallback_to_download, progress_callback
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
            formatting_entities=filter_entities(message.entities, message.text or ""),
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
        fallback_to_download: bool = True,
        progress_callback: Optional[ProgressCallback] = None
    ) -> ForwardResult:
        """Clone a message with media"""
        source_msg_id = message.id
        
        # Check if restricted (need to download/upload)
        is_restricted = self._is_restricted(message)
        
        if is_restricted:
            self.logger.debug("Channel is restricted, will download and upload")
            return await self._download_and_upload(message, target_chat, progress_callback)
        
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
            
        except Exception as e:
            if not fallback_to_download:
                return ForwardResult(
                    success=False,
                    source_msg_id=source_msg_id,
                    error=f"File reference failed: {e}"
                )
            
            self.logger.debug(f"File reference failed, downloading: {e}")
        
        # Fallback: download and re-upload
        return await self._download_and_upload(message, target_chat, progress_callback)
    
    def _is_restricted(self, message: Message) -> bool:
        """Check if message/chat is restricted"""
        # Check message noforwards flag
        if hasattr(message, 'noforwards') and message.noforwards:
            return True
        
        # Check chat noforwards flag
        chat = message.chat
        if hasattr(chat, 'noforwards') and chat.noforwards:
            return True
        
        return False
    
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
                formatting_entities=filter_entities(entities, caption)
            )
            
        elif isinstance(media, MessageMediaDocument):
            # Document (video, file, audio, gif, etc.)
            doc = media.document
            
            # Determine how to send based on attributes
            is_video = self._has_video_attr(doc)
            is_audio = self._has_audio_attr(doc)
            is_voice = self._is_voice(doc)
            is_gif = self._is_gif(doc)
            is_sticker = self._is_sticker(doc)
            
            return await self.client.send_file(
                target_chat,
                file=doc,
                caption=caption,
                formatting_entities=filter_entities(entities, caption),
                voice_note=is_voice,
                video_note=self._is_video_note(doc),
                supports_streaming=is_video,
            )
        else:
            raise ForwardError(f"Unsupported media type: {type(media).__name__}")
    
    async def _download_and_upload(
        self,
        message: Message,
        target_chat,
        progress_callback: Optional[ProgressCallback] = None
    ) -> ForwardResult:
        """
        Download media to temp file and re-upload to target.
        Uses streaming to avoid high memory usage.
        """
        source_msg_id = message.id
        tmp_path = None
        
        try:
            # Create temp file
            suffix = self._get_file_extension(message)
            fd, tmp_path = tempfile.mkstemp(suffix=suffix)
            os.close(fd)
            
            # Download to temp file (streaming, low memory)
            self.logger.debug(f"Downloading to temp file: {tmp_path}")
            await self.client.download_media(
                message,
                file=tmp_path,
                progress_callback=progress_callback
            )
            
            # Get original attributes
            media = message.media
            attributes = None
            mime_type = None
            thumb = None
            
            if isinstance(media, MessageMediaDocument):
                doc = media.document
                attributes = doc.attributes  # Preserve ALL original attributes
                mime_type = doc.mime_type
                # Note: thumb would require separate download, skip for now
            
            caption = message.text or ""
            entities = message.entities
            
            # Determine media type for proper sending
            is_video = self._has_video_attr(doc) if isinstance(media, MessageMediaDocument) else False
            is_audio = self._has_audio_attr(doc) if isinstance(media, MessageMediaDocument) else False
            is_voice = self._is_voice(doc) if isinstance(media, MessageMediaDocument) else False
            is_gif = self._is_gif(doc) if isinstance(media, MessageMediaDocument) else False
            
            # Upload with preserved attributes
            self.logger.debug(f"Uploading with mime_type={mime_type}, attrs={len(attributes) if attributes else 0}")
            
            result = await self.client.send_file(
                target_chat,
                file=tmp_path,
                caption=caption,
                formatting_entities=filter_entities(entities, caption),
                attributes=attributes,  # Preserve original attributes (filename, video size, duration, etc.)
                mime_type=mime_type,    # Preserve MIME type
                voice_note=is_voice,
                supports_streaming=is_video,
                progress_callback=progress_callback
            )
            
            return ForwardResult(
                success=True,
                source_msg_id=source_msg_id,
                target_msg_id=result.id,
                mode_used=ForwardMode.CLONE,
                downloaded=True
            )
            
        except Exception as e:
            self.logger.error(f"Download/upload failed: {e}")
            return ForwardResult(
                success=False,
                source_msg_id=source_msg_id,
                error=f"Download/upload failed: {e}"
            )
        finally:
            # Clean up temp file
            if tmp_path and os.path.exists(tmp_path):
                try:
                    os.unlink(tmp_path)
                except:
                    pass
    
    def _get_file_extension(self, message: Message) -> str:
        """Get file extension from message media"""
        if not message.media:
            return ""
        
        if isinstance(message.media, MessageMediaPhoto):
            return ".jpg"
        
        if isinstance(message.media, MessageMediaDocument):
            doc = message.media.document
            
            # Try to get from filename attribute
            for attr in doc.attributes:
                if isinstance(attr, DocumentAttributeFilename):
                    name = attr.file_name
                    if '.' in name:
                        return '.' + name.rsplit('.', 1)[1]
            
            # Fallback: derive from mime type
            mime = doc.mime_type or ""
            if mime.startswith("video/"):
                return ".mp4"
            elif mime.startswith("audio/"):
                return ".mp3"
            elif mime.startswith("image/"):
                ext = mime.split("/")[1]
                return f".{ext}" if ext else ".jpg"
        
        return ""
    
    def _has_video_attr(self, doc) -> bool:
        """Check if document has video attribute"""
        for attr in doc.attributes:
            if isinstance(attr, DocumentAttributeVideo):
                return True
        return False
    
    def _has_audio_attr(self, doc) -> bool:
        """Check if document has audio attribute"""
        for attr in doc.attributes:
            if isinstance(attr, DocumentAttributeAudio):
                return True
        return False
    
    def _is_voice(self, doc) -> bool:
        """Check if document is voice note"""
        for attr in doc.attributes:
            if isinstance(attr, DocumentAttributeAudio) and attr.voice:
                return True
        return False
    
    def _is_video_note(self, doc) -> bool:
        """Check if document is video note (round video)"""
        for attr in doc.attributes:
            if isinstance(attr, DocumentAttributeVideo) and attr.round_message:
                return True
        return False
    
    def _is_gif(self, doc) -> bool:
        """Check if document is GIF"""
        for attr in doc.attributes:
            if isinstance(attr, DocumentAttributeAnimated):
                return True
        return False
    
    def _is_sticker(self, doc) -> bool:
        """Check if document is sticker"""
        for attr in doc.attributes:
            if isinstance(attr, DocumentAttributeSticker):
                return True
        return False
    
    async def forward_messages(
        self,
        messages: List[Message],
        target_chat,
        mode: ForwardMode = ForwardMode.CLONE,
        fallback_to_download: bool = True,
        progress_callback: Optional[ProgressCallback] = None
    ) -> List[ForwardResult]:
        """
        Forward multiple messages
        
        Args:
            messages: List of messages to forward
            target_chat: Target chat entity
            mode: Forwarding mode
            fallback_to_download: If clone fails, download and re-upload
            progress_callback: Progress callback for each message
        
        Returns:
            List of ForwardResult for each message
        """
        results = []
        
        for message in messages:
            result = await self.forward_message(
                message, target_chat, mode, fallback_to_download, progress_callback
            )
            results.append(result)
        
        return results
    
    async def get_grouped_messages(self, message: Message) -> List[Message]:
        """
        Get all messages belonging to the same media group (album).
        
        Args:
            message: Any message from the group
        
        Returns:
            List of all messages in the group, sorted by ID
        """
        if not message.grouped_id:
            return [message]
        
        chat = message.chat
        grouped_id = message.grouped_id
        
        # Get surrounding messages (media groups are usually consecutive)
        # Fetch messages around the target ID
        msg_ids = list(range(message.id - 10, message.id + 11))
        
        try:
            messages = await self.client.get_messages(chat, ids=msg_ids)
        except Exception as e:
            self.logger.warning(f"Failed to get grouped messages: {e}")
            return [message]
        
        # Filter messages with same grouped_id
        grouped = [
            m for m in messages 
            if m and hasattr(m, 'grouped_id') and m.grouped_id == grouped_id
        ]
        
        # Sort by message ID
        grouped.sort(key=lambda m: m.id)
        
        if not grouped:
            return [message]
        
        self.logger.debug(f"Found {len(grouped)} messages in group {grouped_id}")
        return grouped
    
    async def forward_album(
        self,
        messages: List[Message],
        target_chat,
        mode: ForwardMode = ForwardMode.CLONE,
        progress_callback: Optional[ProgressCallback] = None
    ) -> ForwardResult:
        """
        Forward a media group (album) as a single unit.
        
        Args:
            messages: List of messages in the album (sorted by ID)
            target_chat: Target chat entity
            mode: Forward mode
            progress_callback: Progress callback
        
        Returns:
            ForwardResult for the album
        """
        if not messages:
            return ForwardResult(
                success=False,
                source_msg_id=0,
                error="No messages to forward"
            )
        
        first_msg = messages[0]
        source_msg_id = first_msg.id
        
        try:
            if mode == ForwardMode.DIRECT:
                # Direct forward all messages in the group
                msg_ids = [m.id for m in messages]
                result = await self.client.forward_messages(
                    target_chat,
                    msg_ids,
                    first_msg.chat
                )
                target_ids = [r.id for r in result] if isinstance(result, list) else [result.id]
                
                return ForwardResult(
                    success=True,
                    source_msg_id=source_msg_id,
                    target_msg_id=target_ids[0] if target_ids else None,
                    mode_used=ForwardMode.DIRECT
                )
            
            # Clone mode: download and re-upload as album
            return await self._clone_album(messages, target_chat, progress_callback)
            
        except ChatForwardsRestrictedError:
            self.logger.info("Channel restricts forwarding, using download/upload")
            return await self._clone_album(messages, target_chat, progress_callback)
            
        except Exception as e:
            self.logger.error(f"Forward album failed: {e}")
            return ForwardResult(
                success=False,
                source_msg_id=source_msg_id,
                error=str(e)
            )
    
    async def _clone_album(
        self,
        messages: List[Message],
        target_chat,
        progress_callback: Optional[ProgressCallback] = None
    ) -> ForwardResult:
        """Clone an album by downloading and re-uploading all files"""
        import tempfile
        
        first_msg = messages[0]
        source_msg_id = first_msg.id
        tmp_files = []
        
        try:
            # Download all files to temp directory
            for i, msg in enumerate(messages):
                if not msg.media:
                    continue
                
                suffix = self._get_file_extension(msg)
                fd, tmp_path = tempfile.mkstemp(suffix=suffix)
                os.close(fd)
                
                self.logger.debug(f"Downloading album item {i+1}/{len(messages)}")
                await self.client.download_media(
                    msg,
                    file=tmp_path,
                    progress_callback=progress_callback
                )
                
                # Store file info with caption (only first message has caption typically)
                caption = msg.text or "" if i == 0 else ""
                entities = msg.entities if i == 0 else None
                
                tmp_files.append({
                    'path': tmp_path,
                    'caption': caption,
                    'entities': filter_entities(entities, caption) if entities else None,
                    'message': msg
                })
            
            if not tmp_files:
                return ForwardResult(
                    success=False,
                    source_msg_id=source_msg_id,
                    error="No media files in album"
                )
            
            # Prepare files for send_file (list of paths with captions)
            files = [f['path'] for f in tmp_files]
            caption = tmp_files[0]['caption']
            entities = tmp_files[0]['entities']
            
            self.logger.debug(f"Uploading album with {len(files)} files")
            
            # Send as album
            result = await self.client.send_file(
                target_chat,
                file=files,
                caption=caption,
                formatting_entities=entities,
                progress_callback=progress_callback
            )
            
            # Result is a list of messages for album
            target_ids = [r.id for r in result] if isinstance(result, list) else [result.id]
            
            return ForwardResult(
                success=True,
                source_msg_id=source_msg_id,
                target_msg_id=target_ids[0] if target_ids else None,
                mode_used=ForwardMode.CLONE,
                downloaded=True
            )
            
        except Exception as e:
            self.logger.error(f"Clone album failed: {e}")
            return ForwardResult(
                success=False,
                source_msg_id=source_msg_id,
                error=f"Clone album failed: {e}"
            )
        finally:
            # Clean up temp files
            for f in tmp_files:
                try:
                    if os.path.exists(f['path']):
                        os.unlink(f['path'])
                except:
                    pass
    
    @staticmethod
    def can_forward_direct(message: Message) -> bool:
        """Check if message can be forwarded with direct mode"""
        # Check message noforwards flag
        if hasattr(message, 'noforwards') and message.noforwards:
            return False
        
        # Check if channel restricts forwarding
        chat = message.chat
        if hasattr(chat, 'noforwards') and chat.noforwards:
            return False
        return True
