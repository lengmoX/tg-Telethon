"""
TGF Rule Commands

Manage forwarding rules.
"""

import click

from tgf.cli.utils import (
    console, async_command,
    print_success, print_error, print_info, print_warning,
    create_table, format_chat, confirm_action
)
from tgf.data.database import Database
from tgf.data.models import Rule
from tgf.data.config import get_config


@click.group()
def rule():
    """
    Manage forwarding rules
    
    \b
    Commands:
      add     Add a new rule
      list    List all rules
      edit    Edit a rule
      remove  Remove a rule
    """
    pass


@rule.command('add')
@click.option(
    '--name',
    required=True,
    help='Unique name for this rule',
    metavar='NAME'
)
@click.option(
    '-s', '--source',
    required=True,
    help='Source channel/group',
    metavar='CHAT'
)
@click.option(
    '-t', '--target',
    required=True,
    help='Target channel/group',
    metavar='CHAT'
)
@click.option(
    '-m', '--mode',
    type=click.Choice(['clone', 'direct']),
    default='clone',
    help='Forward mode (default: clone)'
)
@click.option(
    '-i', '--interval',
    type=int,
    default=30,
    help='Sync interval in minutes (default: 30)'
)
@click.option(
    '--note',
    default=None,
    help='Optional note/description'
)
@click.option(
    '--disabled',
    is_flag=True,
    help='Create rule as disabled'
)
@click.pass_context
@async_command
async def add_rule(
    ctx,
    name: str,
    source: str,
    target: str,
    mode: str,
    interval: int,
    note: str,
    disabled: bool
):
    """
    Add a new forwarding rule
    
    \b
    Examples:
      tgf rule add --name news -s @telegram -t me
      tgf rule add --name media -s @channel -t @mychannel --interval 60
    """
    config = ctx.obj["config"]
    
    db = Database(config.db_path)
    await db.connect()
    
    try:
        # Check if name already exists
        existing = await db.get_rule(name=name)
        if existing:
            print_error(f"Rule '{name}' already exists")
            raise click.Abort()
        
        # Create rule
        rule_id = await db.create_rule(
            name=name,
            source_chat=source,
            target_chat=target,
            mode=mode,
            interval_min=interval,
            enabled=not disabled,
            note=note
        )
        
        print_success(f"Rule '{name}' created (ID: {rule_id})")
        
        console.print(f"  Source:   {format_chat(source)}")
        console.print(f"  Target:   {format_chat(target)}")
        console.print(f"  Mode:     {mode}")
        console.print(f"  Interval: {interval} min")
        if note:
            console.print(f"  Note:     {note}")
        
    finally:
        await db.close()


@rule.command('list')
@click.option(
    '--all', 'show_all',
    is_flag=True,
    help='Show all rules including disabled'
)
@click.pass_context
@async_command
async def list_rules(ctx, show_all: bool):
    """
    List all forwarding rules
    
    \b
    Examples:
      tgf rule list
      tgf rule list --all
    """
    config = ctx.obj["config"]
    
    db = Database(config.db_path)
    await db.connect()
    
    try:
        rules = await db.get_all_rules(enabled_only=not show_all)
        
        if not rules:
            print_info("No rules found")
            if not show_all:
                console.print("[dim]Use --all to show disabled rules[/dim]")
            return
        
        table = create_table(
            "Forwarding Rules",
            [
                ("Name", {}),
                ("Source", {}),
                ("Target", {}),
                ("Mode", {}),
                ("Interval", {}),
                ("Status", {}),
            ]
        )
        
        for rule_dict in rules:
            rule = Rule.from_dict(rule_dict)
            status = "[green]●[/green] Enabled" if rule.enabled else "[red]○[/red] Disabled"
            
            table.add_row(
                rule.name,
                format_chat(rule.source_chat),
                format_chat(rule.target_chat),
                rule.mode,
                f"{rule.interval_min}min",
                status
            )
        
        console.print(table)
        console.print(f"\n[dim]Total: {len(rules)} rules[/dim]")
        
    finally:
        await db.close()


@rule.command('edit')
@click.argument('name')
@click.option('-s', '--source', help='New source chat')
@click.option('-t', '--target', help='New target chat')
@click.option('-m', '--mode', type=click.Choice(['clone', 'direct']), help='New mode')
@click.option('-i', '--interval', type=int, help='New interval (minutes)')
@click.option('--note', help='New note')
@click.option('--enable', is_flag=True, help='Enable rule')
@click.option('--disable', is_flag=True, help='Disable rule')
@click.pass_context
@async_command
async def edit_rule(
    ctx,
    name: str,
    source: str,
    target: str,
    mode: str,
    interval: int,
    note: str,
    enable: bool,
    disable: bool
):
    """
    Edit an existing rule
    
    \b
    Examples:
      tgf rule edit myname --interval 60
      tgf rule edit myname --disable
      tgf rule edit myname --source @newchannel
    """
    config = ctx.obj["config"]
    
    db = Database(config.db_path)
    await db.connect()
    
    try:
        # Get existing rule
        rule_dict = await db.get_rule(name=name)
        if not rule_dict:
            print_error(f"Rule '{name}' not found")
            raise click.Abort()
        
        # Build updates
        updates = {}
        if source:
            updates['source_chat'] = source
        if target:
            updates['target_chat'] = target
        if mode:
            updates['mode'] = mode
        if interval:
            updates['interval_min'] = interval
        if note is not None:
            updates['note'] = note
        if enable:
            updates['enabled'] = True
        if disable:
            updates['enabled'] = False
        
        if not updates:
            print_warning("No changes specified")
            return
        
        # Update rule
        success = await db.update_rule(rule_dict['id'], **updates)
        
        if success:
            print_success(f"Rule '{name}' updated")
            for key, val in updates.items():
                console.print(f"  {key}: {val}")
        else:
            print_error("Update failed")
        
    finally:
        await db.close()


@rule.command('remove')
@click.argument('name')
@click.option('--force', '-f', is_flag=True, help='Skip confirmation')
@click.pass_context
@async_command
async def remove_rule(ctx, name: str, force: bool):
    """
    Remove a forwarding rule
    
    \b
    Examples:
      tgf rule remove myname
      tgf rule remove myname -f
    """
    config = ctx.obj["config"]
    
    db = Database(config.db_path)
    await db.connect()
    
    try:
        # Get existing rule
        rule_dict = await db.get_rule(name=name)
        if not rule_dict:
            print_error(f"Rule '{name}' not found")
            raise click.Abort()
        
        rule = Rule.from_dict(rule_dict)
        
        console.print(f"[yellow]Will delete:[/yellow]")
        console.print(f"  Name:   {rule.name}")
        console.print(f"  Source: {format_chat(rule.source_chat)}")
        console.print(f"  Target: {format_chat(rule.target_chat)}")
        
        if not force and not confirm_action("Delete this rule?"):
            return
        
        success = await db.delete_rule(name=name)
        
        if success:
            print_success(f"Rule '{name}' deleted")
        else:
            print_error("Delete failed")
        
    finally:
        await db.close()


@rule.command('show')
@click.argument('name')
@click.pass_context
@async_command
async def show_rule(ctx, name: str):
    """
    Show details of a rule
    
    \b
    Examples:
      tgf rule show myname
    """
    config = ctx.obj["config"]
    namespace = ctx.obj["namespace"]
    
    db = Database(config.db_path)
    await db.connect()
    
    try:
        rule_dict = await db.get_rule(name=name)
        if not rule_dict:
            print_error(f"Rule '{name}' not found")
            raise click.Abort()
        
        rule = Rule.from_dict(rule_dict)
        state_dict = await db.get_state(rule.id, namespace)
        
        status = "[green]Enabled[/green]" if rule.enabled else "[red]Disabled[/red]"
        
        console.print(f"\n[bold]Rule: {rule.name}[/bold] ({status})")
        console.print(f"  Source:     {format_chat(rule.source_chat)}")
        console.print(f"  Target:     {format_chat(rule.target_chat)}")
        console.print(f"  Mode:       {rule.mode}")
        console.print(f"  Interval:   {rule.interval_min} minutes")
        
        if rule.note:
            console.print(f"  Note:       {rule.note}")
        
        if rule.created_at:
            console.print(f"  Created:    {rule.created_at}")
        
        if state_dict:
            console.print(f"\n[bold]Sync State (namespace: {namespace}):[/bold]")
            console.print(f"  Last msg ID:  {state_dict['last_msg_id']}")
            console.print(f"  Last sync:    {state_dict['last_sync_at'] or 'Never'}")
            console.print(f"  Forwarded:    {state_dict['total_forwarded']}")
        else:
            console.print(f"\n[dim]No sync state yet[/dim]")
        
    finally:
        await db.close()
