"""
TGF Backup and Migration Commands

Export and import configuration, rules, and session data.
"""

import json
import shutil
import zipfile
import click
from pathlib import Path
from datetime import datetime
from typing import Optional

from tgf.cli.utils import (
    console, async_command,
    print_success, print_error, print_info, print_warning
)
from tgf.data.database import Database
from tgf.data.config import get_config


@click.group()
def backup():
    """
    Backup and restore data
    
    \b
    Commands:
      export   Export data to backup file
      import   Import data from backup file
      list     List backup contents
    """
    pass


@backup.command('export')
@click.option(
    '-o', '--output',
    default=None,
    help='Output file path (default: <date>.backup.tgf.json)'
)
@click.option(
    '--include-sessions',
    is_flag=True,
    help='Include session files (creates .zip archive)'
)
@click.option(
    '--rules-only',
    is_flag=True,
    help='Export only rules, no states/filters'
)
@click.pass_context
@async_command
async def export_backup(ctx, output: str, include_sessions: bool, rules_only: bool):
    """
    Export data to backup file
    
    \b
    Examples:
      tgf backup export                       # Export to default file
      tgf backup export -o mybackup.json      # Custom filename
      tgf backup export --include-sessions    # Include session files (.zip)
    """
    config = ctx.obj["config"]
    
    db = Database(config.db_path)
    await db.connect()
    
    try:
        # Build backup data
        backup_data = {
            "version": 1,
            "created_at": datetime.now().isoformat(),
            "tool": "tgf",
        }
        
        # Export rules
        rules = await db.get_all_rules(enabled_only=False)
        backup_data["rules"] = rules
        print_info(f"Exporting {len(rules)} rule(s)")
        
        if not rules_only:
            # Export global filters
            filters = await db.get_global_filters(enabled_only=False)
            backup_data["global_filters"] = filters
            print_info(f"Exporting {len(filters)} global filter(s)")
            
            # Export states for all namespaces
            states = []
            for rule in rules:
                state = await db.get_state(rule['id'], config.namespace)
                if state:
                    states.append(state)
            backup_data["states"] = states
            print_info(f"Exporting {len(states)} state record(s)")
        
        # Determine output filename
        if output is None:
            date_str = datetime.now().strftime("%Y%m%d_%H%M%S")
            if include_sessions:
                output = f"{date_str}.backup.tgf.zip"
            else:
                output = f"{date_str}.backup.tgf.json"
        
        output_path = Path(output)
        
        if include_sessions:
            # Create ZIP archive with data and sessions
            if not output_path.suffix == '.zip':
                output_path = output_path.with_suffix('.zip')
            
            with zipfile.ZipFile(output_path, 'w', zipfile.ZIP_DEFLATED) as zf:
                # Add backup data
                zf.writestr('backup.json', json.dumps(backup_data, ensure_ascii=False, indent=2))
                
                # Add session files
                sessions_dir = config.sessions_dir
                if sessions_dir.exists():
                    session_count = 0
                    for session_file in sessions_dir.glob("*.session"):
                        zf.write(session_file, f"sessions/{session_file.name}")
                        session_count += 1
                    print_info(f"Including {session_count} session file(s)")
            
            print_success(f"Backup created: {output_path}")
        else:
            # Create JSON file only
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(backup_data, f, ensure_ascii=False, indent=2)
            
            print_success(f"Backup created: {output_path}")
        
        # Summary
        console.print(f"\n[dim]Backup contents:[/dim]")
        console.print(f"  Rules:   {len(rules)}")
        if not rules_only:
            console.print(f"  Filters: {len(backup_data.get('global_filters', []))}")
            console.print(f"  States:  {len(backup_data.get('states', []))}")
        
    finally:
        await db.close()


@backup.command('import')
@click.argument('file', type=click.Path(exists=True))
@click.option(
    '--merge',
    is_flag=True,
    help='Merge with existing data (skip duplicates)'
)
@click.option(
    '--force',
    is_flag=True,
    help='Overwrite existing rules with same name'
)
@click.option(
    '--include-sessions',
    is_flag=True,
    help='Restore session files from .zip backup'
)
@click.pass_context
@async_command
async def import_backup(ctx, file: str, merge: bool, force: bool, include_sessions: bool):
    """
    Import data from backup file
    
    \b
    Examples:
      tgf backup import backup.json           # Import rules/filters
      tgf backup import backup.zip --include-sessions  # With sessions
      tgf backup import backup.json --merge   # Skip existing rules
      tgf backup import backup.json --force   # Overwrite existing
    """
    config = ctx.obj["config"]
    file_path = Path(file)
    
    # Load backup data
    if file_path.suffix == '.zip':
        with zipfile.ZipFile(file_path, 'r') as zf:
            backup_data = json.loads(zf.read('backup.json').decode('utf-8'))
            
            if include_sessions:
                # Extract sessions
                sessions_dir = config.sessions_dir
                sessions_dir.mkdir(parents=True, exist_ok=True)
                
                session_files = [f for f in zf.namelist() if f.startswith('sessions/')]
                for sf in session_files:
                    zf.extract(sf, config.data_dir)
                    # Move from sessions/ to correct location
                    extracted = config.data_dir / sf
                    target = sessions_dir / Path(sf).name
                    if extracted != target:
                        shutil.move(str(extracted), str(target))
                
                print_info(f"Restored {len(session_files)} session file(s)")
    else:
        with open(file_path, 'r', encoding='utf-8') as f:
            backup_data = json.load(f)
    
    # Validate backup
    if backup_data.get('tool') != 'tgf':
        print_warning("This backup may not be from tgf, proceeding anyway...")
    
    print_info(f"Backup from: {backup_data.get('created_at', 'unknown')}")
    
    db = Database(config.db_path)
    await db.connect()
    
    try:
        rules_imported = 0
        rules_skipped = 0
        filters_imported = 0
        
        # Import rules
        for rule_data in backup_data.get('rules', []):
            name = rule_data.get('name')
            if not name:
                continue
            
            existing = await db.get_rule(name=name)
            
            if existing:
                if force:
                    # Update existing rule
                    await db.update_rule(
                        existing['id'],
                        source_chat=rule_data.get('source_chat'),
                        target_chat=rule_data.get('target_chat'),
                        mode=rule_data.get('mode', 'clone'),
                        interval_min=rule_data.get('interval_min', 30),
                        enabled=rule_data.get('enabled', True),
                        filters=rule_data.get('filters'),
                        note=rule_data.get('note')
                    )
                    rules_imported += 1
                elif merge:
                    rules_skipped += 1
                else:
                    print_warning(f"Rule '{name}' already exists (use --merge or --force)")
                    rules_skipped += 1
            else:
                # Create new rule
                await db.create_rule(
                    name=name,
                    source_chat=rule_data.get('source_chat', ''),
                    target_chat=rule_data.get('target_chat', ''),
                    mode=rule_data.get('mode', 'clone'),
                    interval_min=rule_data.get('interval_min', 30),
                    enabled=rule_data.get('enabled', True),
                    filters=rule_data.get('filters'),
                    note=rule_data.get('note')
                )
                rules_imported += 1
        
        # Import global filters
        for filter_data in backup_data.get('global_filters', []):
            pattern = filter_data.get('pattern')
            if not pattern:
                continue
            
            await db.add_global_filter(
                pattern=pattern,
                action=filter_data.get('action', 'exclude'),
                filter_type=filter_data.get('type', 'contains'),
                case_sensitive=filter_data.get('case_sensitive', False),
                enabled=filter_data.get('enabled', True),
                name=filter_data.get('name')
            )
            filters_imported += 1
        
        print_success("Import complete!")
        console.print(f"  Rules imported: {rules_imported}")
        console.print(f"  Rules skipped:  {rules_skipped}")
        console.print(f"  Filters added:  {filters_imported}")
        
    finally:
        await db.close()


@backup.command('list')
@click.argument('file', type=click.Path(exists=True))
def list_backup(file: str):
    """
    List contents of a backup file
    
    \b
    Examples:
      tgf backup list mybackup.json
    """
    file_path = Path(file)
    
    # Load backup data
    if file_path.suffix == '.zip':
        with zipfile.ZipFile(file_path, 'r') as zf:
            backup_data = json.loads(zf.read('backup.json').decode('utf-8'))
            session_files = [f for f in zf.namelist() if f.startswith('sessions/')]
    else:
        with open(file_path, 'r', encoding='utf-8') as f:
            backup_data = json.load(f)
        session_files = []
    
    console.print(f"\n[bold]Backup: {file_path.name}[/bold]")
    console.print(f"  Created:  {backup_data.get('created_at', 'unknown')}")
    console.print(f"  Version:  {backup_data.get('version', 1)}")
    console.print()
    
    # Rules
    rules = backup_data.get('rules', [])
    console.print(f"[cyan]Rules ({len(rules)}):[/cyan]")
    for r in rules[:10]:  # Show first 10
        status = "●" if r.get('enabled') else "○"
        console.print(f"  {status} {r.get('name')}: {r.get('source_chat')} → {r.get('target_chat')}")
    if len(rules) > 10:
        console.print(f"  ... and {len(rules) - 10} more")
    
    # Filters
    filters = backup_data.get('global_filters', [])
    if filters:
        console.print(f"\n[cyan]Global Filters ({len(filters)}):[/cyan]")
        for f in filters[:5]:
            action = "排除" if f.get('action') == 'exclude' else "包含"
            console.print(f"  {action}: {f.get('pattern')}")
        if len(filters) > 5:
            console.print(f"  ... and {len(filters) - 5} more")
    
    # Sessions
    if session_files:
        console.print(f"\n[cyan]Sessions ({len(session_files)}):[/cyan]")
        for sf in session_files:
            console.print(f"  {Path(sf).name}")
    
    # States
    states = backup_data.get('states', [])
    if states:
        console.print(f"\n[cyan]States ({len(states)}):[/cyan]")
        for s in states[:5]:
            console.print(f"  Rule #{s.get('rule_id')}: last_msg_id={s.get('last_msg_id')}")
