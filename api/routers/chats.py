"""
Chats Router - List chats and export messages

Provides API endpoints for:
- Listing all dialogs/chats
- Exporting messages from a specific chat to JSON
- Downloading exported files

Note: Each request creates a new Telegram connection, which takes 2-5 seconds.
This is expected behavior due to Telegram's protocol requirements.
"""

import json
import logging
import time
from datetime import datetime
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import FileResponse

from api.schemas import (
    ChatInfo,
    ChatListResponse,
    ExportRequest,
    ExportResponse,
    MessageResponse,
)
from api.deps import get_api_config, get_current_user
from tgf.core.client import TGClient
from tgf.core.media import MediaHandler
from tgf.data.config import Config

# Setup logging
logger = logging.getLogger(__name__)

router = APIRouter()

# Export directory for saving exported files
EXPORT_DIR = Path("exports")
EXPORT_DIR.mkdir(exist_ok=True)


def _get_dialog_type(dialog) -> str:
    """Get dialog type string"""
    if dialog.is_channel:
        return "channel"
    elif dialog.is_group:
        return "group"
    elif dialog.is_user:
        return "user"
    return "unknown"


def _message_to_dict(msg, media_handler: MediaHandler, with_content: bool) -> dict:
    """Convert message to dictionary for export"""
    data = {
        "id": msg.id,
        "date": msg.date.isoformat() if msg.date else None,
        "from_id": msg.sender_id,
        "reply_to": msg.reply_to_msg_id if msg.reply_to else None,
        "grouped_id": msg.grouped_id,
    }
    
    if with_content and msg.text:
        data["text"] = msg.text
    
    # Media info
    if msg.media:
        try:
            media_info = media_handler.get_media_info(msg)
            if media_info:
                data["media"] = {
                    "type": media_info.type,
                    "size": media_info.size,
                    "filename": media_info.filename,
                    "mime_type": media_info.mime_type,
                }
                if media_info.duration:
                    data["media"]["duration"] = media_info.duration
                if media_info.width and media_info.height:
                    data["media"]["dimensions"] = {
                        "width": media_info.width,
                        "height": media_info.height
                    }
        except Exception as e:
            logger.warning(f"Failed to get media info for message {msg.id}: {e}")
    
    return data


@router.get("", response_model=ChatListResponse)
async def list_chats(
    limit: int = Query(100, ge=1, le=500, description="Maximum chats to return"),
    chat_type: str = Query("all", pattern="^(all|user|group|channel)$", description="Filter by type"),
    config: Config = Depends(get_api_config),
    _: str = Depends(get_current_user)
):
    """
    List all chats/dialogs
    
    Returns a list of all accessible chats with their basic information.
    Supports filtering by chat type (user, group, channel).
    
    Note: This takes 2-5 seconds as it connects to Telegram servers.
    """
    start_time = time.time()
    logger.info(f"Fetching chat list (limit={limit}, type={chat_type})")
    
    try:
        async with TGClient(config) as client:
            connect_time = time.time()
            logger.debug(f"Connected to Telegram in {connect_time - start_time:.2f}s")
            
            dialogs = await client.get_dialogs(limit=limit)
            fetch_time = time.time()
            logger.debug(f"Fetched {len(dialogs)} dialogs in {fetch_time - connect_time:.2f}s")
            
            # Filter by type
            if chat_type != "all":
                filtered = []
                for d in dialogs:
                    if chat_type == "user" and d.is_user:
                        filtered.append(d)
                    elif chat_type == "group" and d.is_group:
                        filtered.append(d)
                    elif chat_type == "channel" and d.is_channel:
                        filtered.append(d)
                dialogs = filtered
            
            # Convert to response format
            chats = []
            for d in dialogs:
                entity = d.entity
                chats.append(ChatInfo(
                    id=entity.id,
                    name=d.name or "",
                    type=_get_dialog_type(d),
                    username=getattr(entity, 'username', None),
                    unread_count=d.unread_count,
                    last_message_date=d.date.isoformat() if d.date else None,
                ))
            
            total_time = time.time() - start_time
            logger.info(f"Returning {len(chats)} chats in {total_time:.2f}s")
            
            return ChatListResponse(chats=chats, total=len(chats))
            
    except Exception as e:
        logger.error(f"Failed to list chats: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to list chats: {str(e)}")


@router.post("/export", response_model=ExportResponse)
async def export_chat(
    request: ExportRequest,
    config: Config = Depends(get_api_config),
    _: str = Depends(get_current_user)
):
    """
    Export messages from a chat to JSON file
    
    Exports messages from the specified chat with various filtering options.
    Returns the filename which can be downloaded via /export/download/{filename}.
    """
    start_time = time.time()
    logger.info(f"Starting export for chat: {request.chat} (limit={request.limit}, type={request.msg_type})")
    
    try:
        async with TGClient(config) as client:
            media_handler = MediaHandler(client)
            
            # Resolve chat entity
            try:
                entity = await client.get_entity(request.chat)
                logger.debug(f"Resolved chat entity: {entity.id}")
            except Exception as e:
                logger.warning(f"Chat not found: {request.chat} - {e}")
                raise HTTPException(status_code=404, detail=f"Chat not found: {str(e)}")
            
            # Prepare iterator args
            iter_kwargs = {}
            if request.from_id > 0:
                iter_kwargs['min_id'] = request.from_id
            if request.to_id > 0:
                iter_kwargs['max_id'] = request.to_id
            if request.limit:
                iter_kwargs['limit'] = request.limit
            
            messages = []
            count = 0
            
            logger.debug(f"Iterating messages with kwargs: {iter_kwargs}")
            
            async for msg in client.iter_messages(entity, **iter_kwargs):
                # Filter by type
                if request.msg_type != 'all':
                    if request.msg_type == 'media' and not msg.media:
                        continue
                    elif request.msg_type == 'text' and msg.media:
                        continue
                    elif request.msg_type == 'photo' and not msg.photo:
                        continue
                    elif request.msg_type == 'video' and not msg.video:
                        continue
                    elif request.msg_type == 'document' and not msg.document:
                        continue
                
                # Build message data
                msg_data = _message_to_dict(msg, media_handler, request.with_content)
                messages.append(msg_data)
                
                count += 1
                
                # Log progress every 100 messages
                if count % 100 == 0:
                    logger.debug(f"Exported {count} messages...")
                
                if request.limit and count >= request.limit:
                    break
            
            # Generate filename with timestamp
            chat_name = getattr(entity, 'title', None) or getattr(entity, 'first_name', None) or str(entity.id)
            safe_name = "".join(c for c in chat_name if c.isalnum() or c in (' ', '-', '_')).strip()[:30]
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"export_{safe_name}_{timestamp}.json"
            
            # Write to file
            export_data = {
                "chat": {
                    "id": entity.id,
                    "name": chat_name,
                    "username": getattr(entity, 'username', None),
                },
                "exported_at": datetime.now().isoformat(),
                "message_count": len(messages),
                "messages": messages
            }
            
            output_path = EXPORT_DIR / filename
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(export_data, f, ensure_ascii=False, indent=2)
            
            total_time = time.time() - start_time
            logger.info(f"Export complete: {len(messages)} messages to {filename} in {total_time:.2f}s")
            
            return ExportResponse(
                success=True,
                message_count=len(messages),
                filename=filename,
                chat_name=chat_name
            )
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Export failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Export failed: {str(e)}")


@router.get("/export/download/{filename}")
async def download_export(
    filename: str,
    _: str = Depends(get_current_user)
):
    """
    Download an exported JSON file
    
    Returns the exported file for download.
    """
    logger.debug(f"Download request for: {filename}")
    
    # Security: only allow .json files from EXPORT_DIR
    if not filename.endswith('.json') or '..' in filename or '/' in filename or '\\' in filename:
        logger.warning(f"Invalid filename attempted: {filename}")
        raise HTTPException(status_code=400, detail="Invalid filename")
    
    file_path = EXPORT_DIR / filename
    
    if not file_path.exists():
        logger.warning(f"Export file not found: {filename}")
        raise HTTPException(status_code=404, detail="Export file not found")
    
    return FileResponse(
        path=file_path,
        filename=filename,
        media_type="application/json"
    )


@router.get("/export/list")
async def list_exports(
    _: str = Depends(get_current_user)
):
    """
    List all available export files
    """
    exports = []
    for f in EXPORT_DIR.glob("*.json"):
        stat = f.stat()
        exports.append({
            "filename": f.name,
            "size": stat.st_size,
            "created_at": datetime.fromtimestamp(stat.st_ctime).isoformat()
        })
    
    # Sort by creation time, newest first
    exports.sort(key=lambda x: x["created_at"], reverse=True)
    
    logger.debug(f"Found {len(exports)} export files")
    
    return {"exports": exports, "total": len(exports)}
