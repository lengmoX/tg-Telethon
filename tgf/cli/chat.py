"""
TGF Chat Commands

List chats and export messages.
"""

import json
import click
from pathlib import Path
from datetime import datetime
from typing import Optional, List

from rich.table import Table

from tgf.cli.utils import (
    console, async_command, require_login,
    print_success, print_error, print_info, print_warning,
    create_progress
)
from tgf.core.client import TGClient
from tgf.core.media import MediaHandler
from tgf.data.config import get_config


@click.group()
def chat():
    """
    Chat utilities
    
    \b
    Commands:
      ls      List all chats/dialogs
      export  Export messages to JSON
    """
    pass


@chat.command('ls')
@click.option(
    '-o', '--output',
    type=click.Choice(['table', 'json']),
    default='table',
    help='Output format (default: table)'
)
@click.option(
    '--limit',
    type=int,
    default=100,
    help='Maximum number of chats to list'
)
@click.option(
    '--type', 'chat_type',
    type=click.Choice(['all', 'user', 'group', 'channel']),
    default='all',
    help='Filter by chat type'
)
@click.pass_context
@async_command
@require_login
async def list_chats(ctx, output: str, limit: int, chat_type: str):
    """
    List all chats/dialogs
    
    \b
    Examples:
      tgf chat ls                    # List all chats
      tgf chat ls -o json            # Output as JSON
      tgf chat ls --type channel     # List only channels
    """
    config = ctx.obj["config"]
    namespace = ctx.obj["namespace"]
    
    async with TGClient(config, namespace) as client:
        print_info("Fetching dialogs...")
        
        dialogs = await client.get_dialogs(limit=limit)
        
        # Filter by type
        if chat_type != 'all':
            filtered = []
            for d in dialogs:
                if chat_type == 'user' and d.is_user:
                    filtered.append(d)
                elif chat_type == 'group' and d.is_group:
                    filtered.append(d)
                elif chat_type == 'channel' and d.is_channel:
                    filtered.append(d)
            dialogs = filtered
        
        if output == 'json':
            # JSON output
            result = []
            for d in dialogs:
                entity = d.entity
                result.append({
                    "id": entity.id,
                    "name": d.name or "",
                    "type": _get_dialog_type(d),
                    "username": getattr(entity, 'username', None),
                    "unread_count": d.unread_count,
                    "last_message_date": d.date.isoformat() if d.date else None,
                })
            console.print_json(json.dumps(result, ensure_ascii=False, indent=2))
        else:
            # Table output
            table = Table(title=f"Chats ({len(dialogs)})", show_header=True)
            table.add_column("ID", style="dim")
            table.add_column("Type", width=8)
            table.add_column("Name")
            table.add_column("Username", style="cyan")
            table.add_column("Unread", justify="right")
            
            for d in dialogs:
                entity = d.entity
                chat_id = str(entity.id)
                dtype = _get_dialog_type(d)
                name = d.name or "[无名称]"
                username = f"@{entity.username}" if getattr(entity, 'username', None) else ""
                unread = str(d.unread_count) if d.unread_count else ""
                
                # Color by type
                if dtype == "channel":
                    dtype_str = f"[blue]{dtype}[/blue]"
                elif dtype == "group":
                    dtype_str = f"[green]{dtype}[/green]"
                else:
                    dtype_str = dtype
                
                table.add_row(chat_id, dtype_str, name, username, unread)
            
            console.print(table)


@chat.command('export')
@click.option(
    '-c', '--chat',
    required=True,
    help='Chat to export (username, ID, or link)',
    metavar='CHAT'
)
@click.option(
    '-o', '--output',
    default='tgf-export.json',
    help='Output file path (default: tgf-export.json)'
)
@click.option(
    '--limit',
    type=int,
    default=None,
    help='Maximum number of messages to export'
)
@click.option(
    '--from-id',
    type=int,
    default=0,
    help='Start from message ID (export > from_id)'
)
@click.option(
    '--to-id',
    type=int,
    default=0,
    help='End at message ID (export < to_id)'
)
@click.option(
    '--type', 'msg_type',
    type=click.Choice(['all', 'media', 'text', 'photo', 'video', 'document']),
    default='all',
    help='Filter by message type'
)
@click.option(
    '--with-content',
    is_flag=True,
    help='Include message text content'
)
@click.pass_context
@async_command
@require_login
async def export_messages(
    ctx,
    chat: str,
    output: str,
    limit: int,
    from_id: int,
    to_id: int,
    msg_type: str,
    with_content: bool
):
    """
    Export messages from a chat to JSON
    
    \b
    Examples:
      tgf chat export -c @channel                    # Export all media
      tgf chat export -c @channel --limit 100        # Export last 100
      tgf chat export -c @channel --type video       # Only videos
      tgf chat export -c @channel --with-content     # Include text
    """
    config = ctx.obj["config"]
    namespace = ctx.obj["namespace"]
    
    async with TGClient(config, namespace) as client:
        media_handler = MediaHandler(client)
        
        print_info(f"Exporting from: {chat}")
        
        try:
            entity = await client.get_entity(chat)
        except Exception as e:
            print_error(f"Cannot find chat: {e}")
            raise click.Abort()
        
        # Prepare iterator args
        iter_kwargs = {}
        if from_id > 0:
            iter_kwargs['min_id'] = from_id
        if to_id > 0:
            iter_kwargs['max_id'] = to_id
        if limit:
            iter_kwargs['limit'] = limit
        
        messages = []
        count = 0
        
        with create_progress() as progress:
            task = progress.add_task("Exporting...", total=limit or 0)
            
            async for msg in client.iter_messages(entity, **iter_kwargs):
                # Filter by type
                if msg_type != 'all':
                    if msg_type == 'media' and not msg.media:
                        continue
                    elif msg_type == 'text' and msg.media:
                        continue
                    elif msg_type == 'photo' and not msg.photo:
                        continue
                    elif msg_type == 'video' and not msg.video:
                        continue
                    elif msg_type == 'document' and not msg.document:
                        continue
                
                # Build message data
                msg_data = _message_to_dict(msg, media_handler, with_content)
                messages.append(msg_data)
                
                count += 1
                progress.update(task, advance=1)
                
                if limit and count >= limit:
                    break
        
        # Write to file
        output_path = Path(output)
        export_data = {
            "chat": {
                "id": entity.id,
                "name": getattr(entity, 'title', None) or getattr(entity, 'first_name', None) or str(entity.id),
                "username": getattr(entity, 'username', None),
            },
            "exported_at": datetime.now().isoformat(),
            "message_count": len(messages),
            "messages": messages
        }
        
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(export_data, f, ensure_ascii=False, indent=2)
        
        print_success(f"Exported {len(messages)} messages to {output_path}")


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
    """Convert message to dictionary"""
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
    
    return data
