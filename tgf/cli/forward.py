"""
TGF Forward Command

Forward messages between chats with URL/link support.
"""

import re
import json
import click
from pathlib import Path
from typing import List, Tuple, Optional

from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TaskProgressColumn

from tgf.cli.utils import (
    console, async_command, require_login,
    print_success, print_error, print_info, print_warning,
)
from tgf.core.client import TGClient
from tgf.core.forwarder import MessageForwarder, ForwardMode, ForwardResult
from tgf.data.config import get_config


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


def load_from_json(filepath: str) -> List[Tuple[str, int]]:
    """Load message references from exported JSON file"""
    path = Path(filepath)
    if not path.exists():
        raise click.BadParameter(f"File not found: {filepath}")
    
    with open(path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    results = []
    chat_id = data.get('chat', {}).get('id')
    
    if not chat_id:
        raise click.BadParameter(f"Invalid JSON format: missing chat.id")
    
    for msg in data.get('messages', []):
        msg_id = msg.get('id')
        if msg_id:
            results.append((str(chat_id), msg_id))
    
    return results


@click.command('forward')
@click.option(
    '--from', 'sources',
    multiple=True,
    required=True,
    help='Message source: URL (https://t.me/xxx/123) or JSON file',
    metavar='SOURCE'
)
@click.option(
    '--to', 'dest',
    default='me',
    help='Destination chat (default: Saved Messages)',
    metavar='CHAT'
)
@click.option(
    '-m', '--mode',
    type=click.Choice(['clone', 'direct']),
    default='clone',
    help='Forward mode (default: clone)'
)
@click.option(
    '--dry-run',
    is_flag=True,
    help='Preview without forwarding'
)
@click.option(
    '--silent',
    is_flag=True,
    help='Send without notification'
)
@click.pass_context
@async_command
@require_login
async def forward(
    ctx,
    sources: Tuple[str],
    dest: str,
    mode: str,
    dry_run: bool,
    silent: bool
):
    """
    Forward messages from source to destination
    
    \b
    SOURCE can be:
      - Message link: https://t.me/channel/123
      - Private link: https://t.me/c/1234567890/123
      - Exported JSON file: tgf-export.json
    
    \b
    DEST (--to) can be:
      - me (Saved Messages, default)
      - @username
      - Chat ID
      - Channel link
    
    \b
    Examples:
      tgf forward --from https://t.me/durov/1
      tgf forward --from https://t.me/channel/123 --to @mychannel
      tgf forward --from link1 --from link2 --to 123456789
      tgf forward --from export.json --mode direct
    """
    config = ctx.obj["config"]
    namespace = ctx.obj["namespace"]
    
    if dry_run:
        print_warning("DRY RUN - Messages will not be forwarded")
    
    # Parse all sources
    messages_to_forward = []
    
    for source in sources:
        source = source.strip()
        
        # Check if it's a JSON file
        if source.endswith('.json') or Path(source).exists():
            try:
                msgs = load_from_json(source)
                messages_to_forward.extend(msgs)
                print_info(f"Loaded {len(msgs)} messages from {source}")
            except Exception as e:
                print_error(f"Failed to load {source}: {e}")
                continue
        else:
            # Try to parse as link
            parsed = parse_message_link(source)
            if parsed:
                messages_to_forward.append(parsed)
            else:
                print_error(f"Invalid source format: {source}")
    
    if not messages_to_forward:
        print_error("No valid messages to forward")
        raise click.Abort()
    
    print_info(f"Found {len(messages_to_forward)} message(s) to forward")
    print_info(f"Destination: {dest}")
    print_info(f"Mode: {mode}")
    
    async with TGClient(config, namespace) as client:
        forwarder = MessageForwarder(client)
        
        # Get destination entity
        try:
            dest_entity = await client.get_entity(dest)
        except Exception as e:
            print_error(f"Cannot find destination: {e}")
            raise click.Abort()
        
        success_count = 0
        fail_count = 0
        
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TaskProgressColumn(),
            TextColumn("[cyan]{task.fields[status]}[/cyan]"),
            console=console,
            transient=False
        ) as progress:
            main_task = progress.add_task(
                "Forwarding...", 
                total=len(messages_to_forward),
                status=""
            )
            
            # Group messages by source chat for efficiency
            from collections import defaultdict
            by_chat = defaultdict(list)
            for chat_id, msg_id in messages_to_forward:
                by_chat[chat_id].append(msg_id)
            
            for chat_id, msg_ids in by_chat.items():
                try:
                    source_entity = await client.get_entity(chat_id)
                except Exception as e:
                    print_warning(f"Cannot access chat {chat_id}: {e}")
                    fail_count += len(msg_ids)
                    progress.advance(main_task, len(msg_ids))
                    continue
                
                for msg_id in msg_ids:
                    if dry_run:
                        print_info(f"[DRY RUN] Would forward: {chat_id}/{msg_id}")
                        success_count += 1
                    else:
                        try:
                            # Get the message
                            msgs = await client.get_messages(source_entity, ids=[msg_id])
                            if not msgs or not msgs[0]:
                                print_warning(f"Message not found: {msg_id}")
                                fail_count += 1
                                continue
                            
                            msg = msgs[0]
                            
                            # Create progress callback for download/upload
                            def make_progress_callback(description: str):
                                def callback(current, total):
                                    if total > 0:
                                        pct = current * 100 // total
                                        size_mb = total / (1024 * 1024)
                                        progress.update(
                                            main_task, 
                                            status=f"{description} {pct}% ({size_mb:.1f}MB)"
                                        )
                                return callback
                            
                            progress.update(main_task, status="Connecting...")
                            
                            # Forward it with progress callback
                            result = await forwarder.forward_message(
                                msg,
                                dest_entity,
                                mode=ForwardMode(mode),
                                progress_callback=make_progress_callback("Transferring")
                            )
                            
                            if result.success:
                                success_count += 1
                                if result.downloaded:
                                    progress.update(main_task, status="[green]Done (re-uploaded)[/green]")
                                else:
                                    progress.update(main_task, status="[green]Done[/green]")
                            else:
                                fail_count += 1
                                print_warning(f"Failed {msg_id}: {result.error}")
                                
                        except Exception as e:
                            fail_count += 1
                            print_warning(f"Error forwarding {msg_id}: {e}")
                    
                    progress.advance(main_task)
                    progress.update(main_task, status="")
        
        console.print()
        
        if dry_run:
            print_success(f"Would forward {success_count} message(s)")
        else:
            print_success(f"Forwarded {success_count}/{len(messages_to_forward)} message(s)")
            if fail_count > 0:
                print_warning(f"{fail_count} message(s) failed")

