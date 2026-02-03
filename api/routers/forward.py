"""
Forward Router - One-time message forwarding

Provides API endpoints for:
- Forwarding messages by link
- Supporting multiple links
- Album/media group detection

Uses shared Telegram client to avoid session locking.
"""

import re
import logging
import asyncio
from typing import List, Tuple, Optional

from fastapi import APIRouter, Depends, HTTPException

from api.schemas import (
    ForwardRequest,
    ForwardResponse,
    ForwardResultItem,
    M3u8ForwardRequest,
    M3u8ForwardResponse,

)
from api.deps import get_api_config, get_current_user, get_db
from api.services.telegram_client_manager import get_active_client_safe
from tgf.core.forwarder import MessageForwarder, ForwardMode
from tgf.data.config import Config
from tgf.core.forwarder import MessageForwarder, ForwardMode
from tgf.data.config import Config
from tgf.data.database import Database
from tgf.utils.m3u8 import M3u8Downloader
from api.services.task_manager import TaskManager
import time
import os


logger = logging.getLogger(__name__)

router = APIRouter()


# Regex patterns for Telegram message links
LINK_PATTERNS = [
    # Public channel: https://t.me/channel/123
    re.compile(r'https?://t\.me/([a-zA-Z][a-zA-Z0-9_]{3,})/(\d+)(?:/(\d+))?'),
    # Private channel: https://t.me/c/1234567890/123
    re.compile(r'https?://t\.me/c/(\d+)/(\d+)(?:/(\d+))?'),
]


def parse_message_link(link: str) -> Optional[Tuple[str, int]]:
    """
    Parse Telegram message link to (chat, message_id)
    
    Returns:
        Tuple of (chat_identifier, message_id) or None
    """
    link = link.strip()
    
    # Try public channel pattern
    match = LINK_PATTERNS[0].match(link)
    if match:
        username = match.group(1)
        msg_id = int(match.group(2))
        return (f"@{username}", msg_id)
    
    # Try private channel pattern
    match = LINK_PATTERNS[1].match(link)
    if match:
        channel_id = match.group(1)
        msg_id = int(match.group(2))
        # Convert to full channel ID with -100 prefix
        return (f"-100{channel_id}", msg_id)
    
    return None


@router.post("", response_model=ForwardResponse)
async def forward_messages(
    request: ForwardRequest,
    config: Config = Depends(get_api_config),
    db: Database = Depends(get_db),
    _: str = Depends(get_current_user)
):
    """
    Forward messages to destination chat
    
    Supports:
    - Multiple message links (one per line or in array)
    - Public and private channel links
    - Album/media group detection
    - Clone mode (no forward header) or direct mode
    """
    logger.info(f"Forward request: {len(request.links)} links to {request.dest}")
    
    # Parse all links
    messages_to_forward: List[Tuple[str, int, str]] = []  # (chat_id, msg_id, original_link)
    
    for link in request.links:
        link = link.strip()
        if not link:
            continue
            
        parsed = parse_message_link(link)
        if parsed:
            messages_to_forward.append((parsed[0], parsed[1], link))
        else:
            logger.warning(f"Invalid link format: {link}")
    
    if not messages_to_forward:
        raise HTTPException(status_code=400, detail="No valid message links provided")
    
    logger.info(f"Parsed {len(messages_to_forward)} valid messages")
    
    results: List[ForwardResultItem] = []
    succeeded = 0
    failed = 0
    
    try:
        async with get_active_client_safe(db) as client:
            if not client:
                 raise HTTPException(status_code=503, detail="No active Telegram account")

            forwarder = MessageForwarder(client)
            
            # Resolve destination
            try:
                dest_entity = await client.get_entity(request.dest)
                logger.debug(f"Resolved destination: {dest_entity.id}")
            except Exception as e:
                logger.error(f"Cannot find destination: {e}")
                raise HTTPException(status_code=404, detail=f"Destination not found: {request.dest}")
            
            # Group messages by source chat for efficiency
            from collections import defaultdict
            by_chat = defaultdict(list)
            link_map = {}  # (chat_id, msg_id) -> original_link
            
            for chat_id, msg_id, link in messages_to_forward:
                by_chat[chat_id].append(msg_id)
                link_map[(chat_id, msg_id)] = link
            
            # Track already-forwarded message IDs (for albums)
            forwarded_ids = set()
            
            for chat_id, msg_ids in by_chat.items():
                try:
                    source_entity = await client.get_entity(chat_id)
                    logger.debug(f"Resolved source: {chat_id}")
                except Exception as e:
                    logger.warning(f"Cannot access chat {chat_id}: {e}")
                    for msg_id in msg_ids:
                        link = link_map.get((chat_id, msg_id), f"{chat_id}/{msg_id}")
                        results.append(ForwardResultItem(
                            link=link,
                            success=False,
                            error=f"Cannot access source chat: {str(e)}"
                        ))
                        failed += 1
                    continue
                
                for msg_id in msg_ids:
                    link = link_map.get((chat_id, msg_id), f"{chat_id}/{msg_id}")
                    
                    # Skip if already forwarded as part of an album
                    if msg_id in forwarded_ids:
                        results.append(ForwardResultItem(
                            link=link,
                            success=True,
                            error="Forwarded as part of album"
                        ))
                        succeeded += 1
                        continue
                    
                    try:
                        # Get the message
                        msgs = await client.get_messages(source_entity, ids=[msg_id])
                        if not msgs or not msgs[0]:
                            results.append(ForwardResultItem(
                                link=link,
                                success=False,
                                error="Message not found"
                            ))
                            failed += 1
                            continue
                        
                        msg = msgs[0]
                        
                        # Check if message is part of a media group
                        if request.detect_album and msg.grouped_id:
                            grouped_msgs = await forwarder.get_grouped_messages(msg)
                            
                            if len(grouped_msgs) > 1:
                                logger.debug(f"Album detected: {len(grouped_msgs)} items")
                                
                                # Mark all as forwarded
                                for gm in grouped_msgs:
                                    forwarded_ids.add(gm.id)
                                
                                # Forward the whole album
                                result = await forwarder.forward_album(
                                    grouped_msgs,
                                    dest_entity,
                                    mode=ForwardMode(request.mode)
                                )
                            else:
                                result = await forwarder.forward_message(
                                    msg,
                                    dest_entity,
                                    mode=ForwardMode(request.mode)
                                )
                        else:
                            result = await forwarder.forward_message(
                                msg,
                                dest_entity,
                                mode=ForwardMode(request.mode)
                            )
                        
                        if result.success:
                            results.append(ForwardResultItem(
                                link=link,
                                success=True,
                                target_msg_id=result.target_msg_id
                            ))
                            succeeded += 1
                        else:
                            results.append(ForwardResultItem(
                                link=link,
                                success=False,
                                error=result.error
                            ))
                            failed += 1
                            
                    except Exception as e:
                        logger.error(f"Failed to forward {link}: {e}")
                        results.append(ForwardResultItem(
                            link=link,
                            success=False,
                            error=str(e)
                        ))
                        failed += 1
                    
                    # Small delay between messages to avoid rate limiting
                    if len(msg_ids) > 1:
                        await asyncio.sleep(1.0)
        
        logger.info(f"Forward complete: {succeeded}/{len(messages_to_forward)} succeeded")
        
        return ForwardResponse(
            success=failed == 0,
            total=len(messages_to_forward),
            succeeded=succeeded,
            failed=failed,
            results=results
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Forward failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Forward failed: {str(e)}")



@router.post("/m3u8", response_model=M3u8ForwardResponse)
async def forward_m3u8(
    request: M3u8ForwardRequest,
    config: Config = Depends(get_api_config),
    db: Database = Depends(get_db),
    _: str = Depends(get_current_user)
):
    """
    Download M3U8 stream and forward to Telegram (Async Task)
    """
    logger.info(f"M3U8 Forward request: {request.url} to {request.dest}")
    
    try:
        manager = TaskManager.get_instance()
        task_id = await manager.submit_m3u8_task(
            url=request.url,
            dest=request.dest,
            filename=request.filename,
            caption=request.caption
        )
        
        return M3u8ForwardResponse(
            success=True,
            status="queued",
            task_id=task_id
        )
        
    except Exception as e:
        logger.error(f"M3U8 Forward request failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))
    

