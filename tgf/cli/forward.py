"""
TGF Forward Command

Manual message forwarding.
"""

import click

from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TaskProgressColumn

from tgf.cli.utils import (
    console, async_command, require_login,
    print_success, print_error, print_info, print_warning,
    create_table, format_chat
)
from tgf.service.forward_service import ForwardService, ForwardOptions, ForwardProgress
from tgf.core.forwarder import ForwardMode
from tgf.data.config import get_config


@click.command()
@click.option(
    '-s', '--source',
    required=True,
    help='Source channel/group (username, ID, or link)',
    metavar='CHAT'
)
@click.option(
    '-t', '--target',
    required=True,
    help='Target channel/group (username, ID, or link)',
    metavar='CHAT'
)
@click.option(
    '-m', '--mode',
    type=click.Choice(['clone', 'direct']),
    default='clone',
    help='Forward mode: clone (no header) or direct (with header)'
)
@click.option(
    '--limit',
    type=int,
    default=None,
    help='Maximum number of messages to forward'
)
@click.option(
    '--from-id',
    type=int,
    default=0,
    help='Start from this message ID (forward messages > from_id)'
)
@click.option(
    '--to-id',
    type=int,
    default=0,
    help='End at this message ID (forward messages < to_id)'
)
@click.option(
    '--dry-run',
    is_flag=True,
    help='Preview without actually forwarding'
)
@click.option(
    '--no-fallback',
    is_flag=True,
    help='Disable download fallback for restricted channels'
)
@click.pass_context
@async_command
@require_login
async def forward(
    ctx,
    source: str,
    target: str,
    mode: str,
    limit: int,
    from_id: int,
    to_id: int,
    dry_run: bool,
    no_fallback: bool
):
    """
    Forward messages from source to target
    
    \b
    Examples:
      tgf forward -s @durov -t me --limit 10
      tgf forward -s @channel -t @mychannel --mode direct
      tgf forward -s @channel -t me --from-id 1234 --dry-run
    
    \b
    Modes:
      clone:  Copy message content without "Forwarded from" header (default)
      direct: Use native forward API with header
    """
    config = ctx.obj["config"]
    namespace = ctx.obj["namespace"]
    
    if dry_run:
        print_warning("DRY RUN - No messages will be forwarded")
    
    options = ForwardOptions(
        mode=ForwardMode(mode),
        limit=limit,
        from_id=from_id,
        to_id=to_id,
        dry_run=dry_run,
        fallback_to_download=not no_fallback
    )
    
    print_info(f"Source: {format_chat(source)}")
    print_info(f"Target: {format_chat(target)}")
    print_info(f"Mode:   {mode}")
    
    if limit:
        print_info(f"Limit:  {limit}")
    
    console.print()
    
    async with ForwardService(config, namespace) as service:
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TaskProgressColumn(),
            console=console
        ) as progress:
            task_id = progress.add_task("Forwarding...", total=None)
            
            def on_progress(p: ForwardProgress):
                if p.total > 0:
                    progress.update(task_id, total=p.total, completed=p.processed)
                    progress.update(
                        task_id,
                        description=f"Forwarding... ({p.success}✓ {p.failed}✗)"
                    )
            
            try:
                result = await service.forward(
                    source, target, options, on_progress
                )
                
                progress.update(task_id, completed=result.total)
                
            except Exception as e:
                print_error(f"Forward failed: {e}")
                raise click.Abort()
    
    console.print()
    
    # Print summary
    if dry_run:
        print_success(f"Would forward {result.total} messages")
    else:
        print_success(f"Forwarded {result.success}/{result.total} messages")
        
        if result.failed > 0:
            print_warning(f"{result.failed} messages failed")
    
    # Show stats
    elapsed = result.elapsed_seconds
    rate = result.success / elapsed if elapsed > 0 else 0
    
    console.print(f"  [dim]Time: {elapsed:.1f}s ({rate:.1f} msg/s)[/dim]")


@click.command('preview')
@click.option(
    '-s', '--source',
    required=True,
    help='Source channel/group',
    metavar='CHAT'
)
@click.option(
    '--limit',
    type=int,
    default=10,
    help='Number of messages to preview'
)
@click.option(
    '--from-id',
    type=int,
    default=0,
    help='Start from this message ID'
)
@click.pass_context
@async_command
@require_login
async def preview(ctx, source: str, limit: int, from_id: int):
    """
    Preview messages without forwarding
    
    \b
    Examples:
      tgf preview -s @channel --limit 5
    """
    config = ctx.obj["config"]
    namespace = ctx.obj["namespace"]
    
    print_info(f"Previewing messages from: {format_chat(source)}")
    console.print()
    
    async with ForwardService(config, namespace) as service:
        try:
            messages = await service.preview_messages(source, limit, from_id)
            
            if not messages:
                print_info("No messages found")
                return
            
            table = create_table(
                f"Messages in {source}",
                ["ID", "Date", "Type", "Content"]
            )
            
            for msg in messages:
                msg_type = msg.get("media_type", "text")
                if msg.get("media_size"):
                    msg_type = f"{msg_type} ({msg['media_size']})"
                
                content = msg.get("text") or "[media only]"
                
                table.add_row(
                    str(msg["id"]),
                    msg.get("date", "?")[:19] if msg.get("date") else "?",
                    msg_type,
                    content[:50] + "..." if len(content) > 50 else content
                )
            
            console.print(table)
            
        except Exception as e:
            print_error(f"Preview failed: {e}")
            raise click.Abort()
