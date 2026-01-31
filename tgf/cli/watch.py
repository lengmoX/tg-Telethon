"""
TGF Watch Command

Scheduled monitoring and syncing with daemon support.
"""

import os
import sys
import signal
import subprocess
import click
from pathlib import Path

from rich.live import Live
from rich.table import Table
from rich.panel import Panel

from tgf.cli.utils import (
    console, async_command, require_login,
    print_success, print_error, print_info, print_warning,
    create_table, format_chat, confirm_action
)
from tgf.service.watch_service import WatchService, SyncResult
from tgf.data.database import Database
from tgf.data.models import Rule, State
from tgf.data.config import get_config


def get_pid_file(config) -> Path:
    """Get path to PID file"""
    return config.data_dir / "tgf-watch.pid"


def get_log_file(config) -> Path:
    """Get path to daemon log file"""
    return config.logs_dir / "watch.log"


def is_process_running(pid: int) -> bool:
    """Check if a process with given PID is running"""
    try:
        os.kill(pid, 0)
        return True
    except (OSError, ProcessLookupError):
        return False


def read_pid(config) -> int | None:
    """Read PID from file"""
    pid_file = get_pid_file(config)
    if pid_file.exists():
        try:
            pid = int(pid_file.read_text().strip())
            if is_process_running(pid):
                return pid
            # Clean up stale PID file
            pid_file.unlink()
        except (ValueError, OSError):
            pass
    return None


def write_pid(config, pid: int):
    """Write PID to file"""
    get_pid_file(config).write_text(str(pid))


def remove_pid(config):
    """Remove PID file"""
    pid_file = get_pid_file(config)
    if pid_file.exists():
        pid_file.unlink()


@click.group(invoke_without_command=True)
@click.argument('rule_name', required=False, default=None)
@click.option(
    '--once',
    is_flag=True,
    help='Run sync once and exit'
)
@click.option(
    '-d', '--daemon',
    is_flag=True,
    help='Run in background (daemon mode)'
)
@click.pass_context
def watch(ctx, rule_name: str, once: bool, daemon: bool):
    """
    Start watching and syncing rules
    
    \b
    If RULE_NAME is specified, only that rule is watched.
    Otherwise, all enabled rules are watched.
    
    \b
    Examples:
      tgf watch             # Watch all enabled rules (foreground)
      tgf watch -d          # Watch in background (daemon mode)
      tgf watch stop        # Stop background watcher
      tgf watch status      # Check if watcher is running
      tgf watch myname      # Watch specific rule
      tgf watch --once      # Sync all once and exit
    """
    # If subcommand is invoked, don't run default
    if ctx.invoked_subcommand is not None:
        return
    
    # Run the actual watch
    ctx.invoke(_watch_run, rule_name=rule_name, once=once, daemon=daemon)


@watch.command('start')
@click.argument('rule_name', required=False, default=None)
@click.pass_context
def watch_start(ctx, rule_name: str):
    """Start watching in background (daemon mode)"""
    ctx.invoke(_watch_run, rule_name=rule_name, once=False, daemon=True)


@watch.command('stop')
@click.pass_context
def watch_stop(ctx):
    """Stop the background watcher"""
    config = get_config()
    
    pid = read_pid(config)
    if pid is None:
        print_warning("Watcher is not running")
        return
    
    try:
        if sys.platform == 'win32':
            # Windows: use taskkill
            subprocess.run(['taskkill', '/F', '/PID', str(pid)], 
                         capture_output=True)
        else:
            # Unix: send SIGTERM
            os.kill(pid, signal.SIGTERM)
        
        remove_pid(config)
        print_success(f"Watcher stopped (PID: {pid})")
    except Exception as e:
        print_error(f"Failed to stop watcher: {e}")


@watch.command('status')
@click.pass_context
def watch_status(ctx):
    """Check if watcher is running"""
    config = get_config()
    
    pid = read_pid(config)
    if pid:
        print_success(f"Watcher is running (PID: {pid})")
        
        # Show log file location
        log_file = get_log_file(config)
        if log_file.exists():
            console.print(f"  Log file: {log_file}")
    else:
        print_info("Watcher is not running")
        console.print("  Start with: tgf watch -d")


@click.command('_watch_run', hidden=True)
@click.argument('rule_name', required=False, default=None)
@click.option('--once', is_flag=True)
@click.option('-d', '--daemon', is_flag=True)
@click.pass_context
@async_command
@require_login
async def _watch_run(ctx, rule_name: str, once: bool, daemon: bool):
    """Internal command to run watch"""
    config = ctx.obj["config"]
    namespace = ctx.obj["namespace"]
    
    # Daemon mode
    if daemon:
        # Check if already running
        existing_pid = read_pid(config)
        if existing_pid:
            print_warning(f"Watcher already running (PID: {existing_pid})")
            print_info("Use 'tgf watch stop' to stop it first")
            return
        
        # Start daemon process
        _start_daemon(config, namespace, rule_name)
        return
    
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


def _start_daemon(config, namespace: str, rule_name: str | None):
    """Start watch as a background daemon process"""
    import sys
    
    # Build command
    cmd = [sys.executable, '-m', 'tgf', '-n', namespace, 'watch']
    if rule_name:
        cmd.append(rule_name)
    
    # Log file
    log_file = get_log_file(config)
    log_file.parent.mkdir(parents=True, exist_ok=True)
    
    if sys.platform == 'win32':
        # Windows: use subprocess with DETACHED_PROCESS
        DETACHED_PROCESS = 0x00000008
        CREATE_NO_WINDOW = 0x08000000
        
        with open(log_file, 'a') as log:
            process = subprocess.Popen(
                cmd,
                stdout=log,
                stderr=log,
                stdin=subprocess.DEVNULL,
                creationflags=DETACHED_PROCESS | CREATE_NO_WINDOW,
                cwd=config.data_dir
            )
        pid = process.pid
    else:
        # Unix: use nohup-style background
        with open(log_file, 'a') as log:
            process = subprocess.Popen(
                cmd,
                stdout=log,
                stderr=log,
                stdin=subprocess.DEVNULL,
                start_new_session=True,
                cwd=config.data_dir
            )
        pid = process.pid
    
    # Save PID
    write_pid(config, pid)
    
    print_success(f"Watcher started in background (PID: {pid})")
    console.print(f"  Log file: {log_file}")
    console.print()
    console.print("  [dim]Check status:[/dim] tgf watch status")
    console.print("  [dim]Stop watcher:[/dim]  tgf watch stop")
    console.print("  [dim]View logs:[/dim]     tail -f " + str(log_file))


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
        
        # Check if watcher is running
        pid = read_pid(config)
        if pid:
            console.print(f"[green]● Watcher running[/green] (PID: {pid})")
        else:
            console.print("[dim]○ Watcher not running[/dim]")
        console.print()
        
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
