"""
TGF Filter Commands

Manage global message filters.
"""

import click

from rich.table import Table

from tgf.cli.utils import (
    console, async_command,
    print_success, print_error, print_info, print_warning
)
from tgf.data.database import Database
from tgf.data.config import get_config
from tgf.utils.filter import FilterType, FilterAction


@click.group()
def filter():
    """
    Manage global message filters
    
    \b
    Global filters apply to ALL rules during watch mode.
    Use to exclude spam, ads, or unwanted content.
    
    \b
    Commands:
      add     Add a global filter
      list    List all global filters
      remove  Remove a global filter
      test    Test filters against text
    """
    pass


@filter.command('add')
@click.argument('pattern')
@click.option(
    '--action', '-a',
    type=click.Choice(['exclude', 'include']),
    default='exclude',
    help='Filter action (default: exclude)'
)
@click.option(
    '--type', '-t', 'filter_type',
    type=click.Choice(['contains', 'keyword', 'regex', 'starts', 'ends']),
    default='contains',
    help='Match type (default: contains)'
)
@click.option(
    '--case-sensitive', '-c',
    is_flag=True,
    help='Case sensitive matching'
)
@click.option(
    '--name', '-n',
    help='Optional filter name for reference'
)
@click.pass_context
@async_command
async def add_filter(ctx, pattern: str, action: str, filter_type: str, case_sensitive: bool, name: str):
    """
    Add a global filter
    
    \b
    Examples:
      tgf filter add "广告"                      # Exclude messages containing 广告
      tgf filter add "推广" --name spam          # With a name
      tgf filter add "重要" --action include     # Include filter (override excludes)
      tgf filter add "^AD:" --type regex         # Regex pattern
      tgf filter add "promo" --type keyword      # Word boundary match
    """
    config = ctx.obj["config"]
    
    db = Database(config.db_path)
    await db.connect()
    
    try:
        filter_id = await db.add_global_filter(
            pattern=pattern,
            action=action,
            filter_type=filter_type,
            case_sensitive=case_sensitive,
            name=name
        )
        
        action_str = "排除" if action == "exclude" else "包含"
        print_success(f"已添加全局过滤器 #{filter_id}: {action_str} \"{pattern}\"")
        
    finally:
        await db.close()


@filter.command('list')
@click.option('--all', '-a', 'show_all', is_flag=True, help='Show disabled filters too')
@click.pass_context
@async_command
async def list_filters(ctx, show_all: bool):
    """List all global filters"""
    config = ctx.obj["config"]
    
    db = Database(config.db_path)
    await db.connect()
    
    try:
        filters = await db.get_global_filters(enabled_only=not show_all)
        
        if not filters:
            print_info("没有全局过滤器")
            return
        
        table = Table(title="全局过滤器", show_header=True)
        table.add_column("ID", style="dim", width=4)
        table.add_column("动作", width=6)
        table.add_column("类型", width=10)
        table.add_column("模式")
        table.add_column("名称", style="cyan")
        table.add_column("状态", width=6)
        
        for f in filters:
            action = "[red]排除[/red]" if f["action"] == "exclude" else "[green]包含[/green]"
            status = "[green]✓[/green]" if f["enabled"] else "[dim]✗[/dim]"
            name = f["name"] or ""
            
            table.add_row(
                str(f["id"]),
                action,
                f["type"],
                f["pattern"],
                name,
                status
            )
        
        console.print(table)
        
    finally:
        await db.close()


@filter.command('remove')
@click.argument('filter_id', type=int)
@click.option('--force', '-f', is_flag=True, help='Skip confirmation')
@click.pass_context
@async_command
async def remove_filter(ctx, filter_id: int, force: bool):
    """Remove a global filter by ID"""
    config = ctx.obj["config"]
    
    if not force:
        if not click.confirm(f"确定删除过滤器 #{filter_id}?"):
            return
    
    db = Database(config.db_path)
    await db.connect()
    
    try:
        if await db.delete_global_filter(filter_id):
            print_success(f"已删除过滤器 #{filter_id}")
        else:
            print_error(f"过滤器 #{filter_id} 不存在")
    finally:
        await db.close()


@filter.command('test')
@click.argument('text')
@click.pass_context
@async_command
async def test_filter(ctx, text: str):
    """
    Test if text would be filtered
    
    \b
    Examples:
      tgf filter test "这是一条包含广告的消息"
    """
    from tgf.utils.filter import FilterConfig, FilterRule, MessageFilter
    
    config = ctx.obj["config"]
    
    db = Database(config.db_path)
    await db.connect()
    
    try:
        filters = await db.get_global_filters(enabled_only=True)
        
        if not filters:
            print_info("没有启用的全局过滤器")
            console.print(f"[green]✓ 消息会被转发[/green]")
            return
        
        # Build filter config
        global_config = FilterConfig()
        for f in filters:
            global_config.rules.append(FilterRule(
                pattern=f["pattern"],
                action=FilterAction(f["action"]),
                filter_type=FilterType(f["type"]),
                case_sensitive=bool(f["case_sensitive"]),
                name=f["name"]
            ))
        
        msg_filter = MessageFilter(global_filters=global_config)
        should_forward, reason = msg_filter.should_forward(text)
        
        console.print(f"\n[dim]测试文本:[/dim] {text}\n")
        
        if should_forward:
            console.print(f"[green]✓ 消息会被转发[/green]")
        else:
            console.print(f"[red]✗ 消息会被过滤[/red]")
            console.print(f"[yellow]原因: {reason}[/yellow]")
    
    finally:
        await db.close()
