"""
TGF Backup and Migration Commands

Export and import all data including sessions.
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
    Backup and restore all data
    
    \b
    Commands:
      export   Export all data to backup file
      import   Restore data from backup file
      list     List backup contents
    """
    pass


@backup.command('export')
@click.option(
    '-o', '--output',
    default=None,
    help='Output file path (default: tgf_backup_<date>.zip)'
)
@click.option(
    '--no-sessions',
    is_flag=True,
    help='Exclude session files (login info)'
)
@click.option(
    '--no-db',
    is_flag=True,
    help='Exclude database file'
)
@click.pass_context
@async_command
async def export_backup(ctx, output: str, no_sessions: bool, no_db: bool):
    """
    Export all data to backup file
    
    \b
    Default exports:
      - Session files (login credentials)
      - Database (rules, filters, states)
      - .env file (if exists)
    
    \b
    Examples:
      tgf backup export                    # Full backup
      tgf backup export -o my_backup.zip   # Custom filename
      tgf backup export --no-sessions      # Without session files
    """
    config = ctx.obj["config"]
    
    # Determine output filename
    if output is None:
        date_str = datetime.now().strftime("%Y%m%d_%H%M%S")
        output = f"tgf_backup_{date_str}.zip"
    
    output_path = Path(output)
    if not output_path.suffix == '.zip':
        output_path = output_path.with_suffix('.zip')
    
    # Build metadata
    metadata = {
        "version": 2,
        "created_at": datetime.now().isoformat(),
        "tool": "tgf",
        "namespace": config.namespace,
        "contents": []
    }
    
    console.print("\n[bold cyan]═══ TGF 备份 ═══[/bold cyan]\n")
    
    with zipfile.ZipFile(output_path, 'w', zipfile.ZIP_DEFLATED) as zf:
        
        # 1. Export database
        if not no_db and config.db_path.exists():
            zf.write(config.db_path, "tgf.db")
            metadata["contents"].append("database")
            db_size = config.db_path.stat().st_size / 1024
            print_info(f"数据库: tgf.db ({db_size:.1f} KB)")
        
        # 2. Export session files
        if not no_sessions and config.sessions_dir.exists():
            session_count = 0
            for session_file in config.sessions_dir.glob("*.session"):
                zf.write(session_file, f"sessions/{session_file.name}")
                session_count += 1
            
            # Also include journal files if they exist
            for journal_file in config.sessions_dir.glob("*.session-journal"):
                zf.write(journal_file, f"sessions/{journal_file.name}")
            
            if session_count > 0:
                metadata["contents"].append("sessions")
                print_info(f"会话文件: {session_count} 个账号")
        
        # 3. Export .env file if exists
        env_files = [
            config.data_dir / ".env",
            Path.cwd() / ".env",
        ]
        for env_file in env_files:
            if env_file.exists():
                zf.write(env_file, ".env")
                metadata["contents"].append("env")
                print_info(f"环境配置: .env")
                break
        
        # 4. Export logs (optional, just last log file)
        if config.logs_dir.exists():
            log_files = list(config.logs_dir.glob("*.log"))
            if log_files:
                latest_log = max(log_files, key=lambda p: p.stat().st_mtime)
                zf.write(latest_log, f"logs/{latest_log.name}")
                metadata["contents"].append("logs")
        
        # 5. Write metadata
        zf.writestr('metadata.json', json.dumps(metadata, ensure_ascii=False, indent=2))
    
    # Summary
    file_size = output_path.stat().st_size / 1024
    
    console.print()
    print_success(f"备份完成: {output_path}")
    console.print(f"  文件大小: {file_size:.1f} KB")
    console.print(f"  包含内容: {', '.join(metadata['contents'])}")
    console.print()
    console.print("[dim]恢复命令: tgf backup import " + str(output_path) + "[/dim]")


@backup.command('import')
@click.argument('file', type=click.Path(exists=True))
@click.option(
    '--force',
    is_flag=True,
    help='Overwrite existing files without asking'
)
@click.option(
    '--no-sessions',
    is_flag=True,
    help='Skip restoring session files'
)
@click.option(
    '--no-db',
    is_flag=True,
    help='Skip restoring database'
)
@click.pass_context
@async_command
async def import_backup(ctx, file: str, force: bool, no_sessions: bool, no_db: bool):
    """
    Restore data from backup file
    
    \b
    Examples:
      tgf backup import backup.zip         # Full restore
      tgf backup import backup.zip --force # Overwrite existing
      tgf backup import backup.zip --no-sessions  # Without sessions
    """
    config = ctx.obj["config"]
    file_path = Path(file)
    
    if not file_path.suffix == '.zip':
        print_error("备份文件必须是 .zip 格式")
        return
    
    console.print("\n[bold cyan]═══ TGF 恢复 ═══[/bold cyan]\n")
    
    with zipfile.ZipFile(file_path, 'r') as zf:
        # Read metadata
        try:
            metadata = json.loads(zf.read('metadata.json').decode('utf-8'))
            print_info(f"备份时间: {metadata.get('created_at', 'unknown')}")
            print_info(f"备份内容: {', '.join(metadata.get('contents', []))}")
        except KeyError:
            # Legacy backup format
            metadata = {"contents": []}
            print_warning("旧版备份格式，尝试恢复...")
        
        console.print()
        
        # 1. Restore database
        if not no_db and 'tgf.db' in zf.namelist():
            if config.db_path.exists() and not force:
                if not click.confirm("数据库已存在，是否覆盖?"):
                    print_info("跳过数据库")
                else:
                    zf.extract('tgf.db', config.data_dir)
                    print_success("已恢复: 数据库")
            else:
                zf.extract('tgf.db', config.data_dir)
                print_success("已恢复: 数据库")
        
        # 2. Restore session files
        if not no_sessions:
            session_files = [f for f in zf.namelist() if f.startswith('sessions/') and not f.endswith('/')]
            if session_files:
                config.sessions_dir.mkdir(parents=True, exist_ok=True)
                
                for sf in session_files:
                    target = config.sessions_dir / Path(sf).name
                    
                    if target.exists() and not force:
                        if not click.confirm(f"会话 {Path(sf).name} 已存在，是否覆盖?"):
                            continue
                    
                    # Extract to temp then move
                    zf.extract(sf, config.data_dir)
                    extracted = config.data_dir / sf
                    shutil.move(str(extracted), str(target))
                
                # Clean up sessions directory from extraction
                sessions_tmp = config.data_dir / "sessions"
                if sessions_tmp.exists() and sessions_tmp != config.sessions_dir:
                    shutil.rmtree(sessions_tmp, ignore_errors=True)
                
                print_success(f"已恢复: {len(session_files)} 个会话文件")
        
        # 3. Restore .env file
        if '.env' in zf.namelist():
            env_target = config.data_dir / ".env"
            
            if env_target.exists() and not force:
                if click.confirm(".env 已存在，是否覆盖?"):
                    zf.extract('.env', config.data_dir)
                    print_success("已恢复: .env")
            else:
                zf.extract('.env', config.data_dir)
                print_success("已恢复: .env")
        
        # 4. Restore logs (optional)
        log_files = [f for f in zf.namelist() if f.startswith('logs/')]
        if log_files:
            config.logs_dir.mkdir(parents=True, exist_ok=True)
            for lf in log_files:
                zf.extract(lf, config.data_dir)
    
    console.print()
    print_success("恢复完成!")
    console.print("\n[dim]使用 'tgf rule list' 查看已恢复的规则[/dim]")


@backup.command('list')
@click.argument('file', type=click.Path(exists=True))
def list_backup(file: str):
    """
    List contents of a backup file
    
    \b
    Examples:
      tgf backup list mybackup.zip
    """
    file_path = Path(file)
    
    if not file_path.suffix == '.zip':
        print_error("备份文件必须是 .zip 格式")
        return
    
    console.print(f"\n[bold]备份文件: {file_path.name}[/bold]")
    
    with zipfile.ZipFile(file_path, 'r') as zf:
        # Read metadata
        try:
            metadata = json.loads(zf.read('metadata.json').decode('utf-8'))
            console.print(f"  创建时间: {metadata.get('created_at', 'unknown')}")
            console.print(f"  版本: {metadata.get('version', 1)}")
            console.print(f"  命名空间: {metadata.get('namespace', 'default')}")
        except KeyError:
            console.print("  [dim]旧版备份格式[/dim]")
        
        console.print()
        
        # List all files
        all_files = zf.namelist()
        
        # Database
        if 'tgf.db' in all_files:
            info = zf.getinfo('tgf.db')
            console.print(f"[cyan]数据库:[/cyan] tgf.db ({info.file_size / 1024:.1f} KB)")
        
        # Sessions
        sessions = [f for f in all_files if f.startswith('sessions/') and not f.endswith('/')]
        if sessions:
            console.print(f"\n[cyan]会话文件 ({len(sessions)}):[/cyan]")
            for sf in sessions:
                info = zf.getinfo(sf)
                console.print(f"  {Path(sf).name} ({info.file_size / 1024:.1f} KB)")
        
        # Env
        if '.env' in all_files:
            console.print(f"\n[cyan]环境配置:[/cyan] .env")
        
        # Logs
        logs = [f for f in all_files if f.startswith('logs/')]
        if logs:
            console.print(f"\n[cyan]日志文件:[/cyan] {len(logs)} 个")
        
        # Total size
        total_size = sum(zf.getinfo(f).file_size for f in all_files)
        console.print(f"\n[dim]总大小: {total_size / 1024:.1f} KB (压缩前)[/dim]")
