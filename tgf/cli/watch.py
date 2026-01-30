"""
TGF Watch Command

Scheduled monitoring and syncing.
"""

import signal
import click

from rich.live import Live
from rich.table import Table
from rich.panel import Panel

from tgf.cli.utils import (
    console, async_command, require_login,
    print_success, print_error, print_info, print_warning,
    create_table, format_chat
)
from tgf.service.watch_service import WatchService, SyncResult
from tgf.data.database import Database
from tgf.data.models import Rule, State
from tgf.data.config import get_config


@click.command()
@click.argument('rule_name', required=False, default=None)
@click.option(
    '--once',
    is_flag=True,
    help='Run sync once and exit'
)
@click.pass_context
@async_command
@require_login
async def watch(ctx, rule_name: str, once: bool):
    """
    Start watching and syncing rules
    
    \b
    If RULE_NAME is specified, only that rule is watched.
    Otherwise, all enabled rules are watched.
    
    \b
    Examples:
      tgf watch             # Watch all enabled rules
      tgf watch myname      # Watch specific rule
      tgf watch --once      # Sync all once and exit
    """
    config = ctx.obj["config"]
    namespace = ctx.obj["namespace"]
    
    async with WatchService(config, namespace) as service:
        if once:
            # Single sync
            if rule_name:
                print_info(f"Syncing rule: {rule_name}")
                result = await service.sync_rule(rule_name)
                _print_sync_result(result)
            else:
                print_info("Syncing all enabled rules...")
                results = await service.sync_all(
                    on_rule_start=lambda n: print_info(f"Syncing: {n}"),
                    on_rule_complete=_print_sync_result
                )
                
                # Summary
                total_found = sum(r.messages_found for r in results)
                total_forwarded = sum(r.messages_forwarded for r in results)
                total_failed = sum(r.messages_failed for r in results)
                
                console.print()
                print_success(f"Sync complete: {len(results)} rules")
                console.print(f"  Found:     {total_found}")
                console.print(f"  Forwarded: {total_forwarded}")
                if total_failed > 0:
                    console.print(f"  [red]Failed: {total_failed}[/red]")
            
            return
        
        # Continuous watch mode
        if rule_name:
            print_info(f"Watching rule: {rule_name}")
        else:
            print_info("Watching all enabled rules")
        
        print_info("Press Ctrl+C to stop")
        console.print()
        
        # Handle Ctrl+C
        def signal_handler(sig, frame):
            print_warning("\nStopping watch...")
            service.stop()
        
        signal.signal(signal.SIGINT, signal_handler)
        
        try:
            await service.watch(
                rule_name=rule_name,
                on_sync=_on_sync_cycle
            )
        except KeyboardInterrupt:
            pass
        
        print_success("Watch stopped")


@click.command()
@click.argument('rule_name', required=False, default=None)
@click.pass_context
@async_command
async def status(ctx, rule_name: str):
    """
    Show status of rules and sync state
    
    \b
    Examples:
      tgf status           # Show all rules status
      tgf status myname    # Show specific rule status
    """
    config = ctx.obj["config"]
    namespace = ctx.obj["namespace"]
    
    db = Database(config.db_path)
    await db.connect()
    
    try:
        if rule_name:
            rule_dict = await db.get_rule(name=rule_name)
            if not rule_dict:
                print_error(f"Rule '{rule_name}' not found")
                raise click.Abort()
            rules = [rule_dict]
        else:
            rules = await db.get_all_rules()
        
        if not rules:
            print_info("No rules found")
            return
        
        table = create_table(
            f"Rule Status (namespace: {namespace})",
            [
                ("Rule", {}),
                ("Source → Target", {}),
                ("Status", {}),
                ("Last Msg ID", {}),
                ("Forwarded", {}),
                ("Last Sync", {}),
            ]
        )
        
        for rule_dict in rules:
            rule = Rule.from_dict(rule_dict)
            state_dict = await db.get_state(rule.id, namespace)
            
            status_str = "[green]●[/green]" if rule.enabled else "[red]○[/red]"
            route = f"{format_chat(rule.source_chat)} → {format_chat(rule.target_chat)}"
            
            if state_dict:
                last_msg_id = str(state_dict['last_msg_id'])
                forwarded = str(state_dict['total_forwarded'])
                last_sync = state_dict['last_sync_at'][:16] if state_dict['last_sync_at'] else "Never"
            else:
                last_msg_id = "0"
                forwarded = "0"
                last_sync = "Never"
            
            table.add_row(
                rule.name,
                route,
                status_str,
                last_msg_id,
                forwarded,
                last_sync
            )
        
        console.print(table)
        
    finally:
        await db.close()


def _print_sync_result(result: SyncResult):
    """Print single sync result"""
    if result.error:
        print_error(f"[{result.rule_name}] {result.error}")
    elif result.messages_found == 0:
        console.print(f"  [{result.rule_name}] [dim]No new messages[/dim]")
    else:
        status = f"[green]{result.messages_forwarded}[/green] forwarded"
        if result.messages_failed > 0:
            status += f", [red]{result.messages_failed}[/red] failed"
        console.print(f"  [{result.rule_name}] {result.messages_found} found, {status}")


def _on_sync_cycle(results: list):
    """Called after each sync cycle"""
    console.print(f"\n[dim]--- Sync cycle complete ---[/dim]")
    
    for result in results:
        _print_sync_result(result)
    
    console.print()
