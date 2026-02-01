"""
Watcher Router - Control background watcher process
"""

import os
import sys
import signal
import subprocess
from pathlib import Path
from typing import List

from fastapi import APIRouter, Depends, HTTPException

from api.schemas import WatcherStatus, LogEntry, LogsResponse, MessageResponse
from api.deps import get_api_config, get_db, get_current_user
from tgf.data.config import Config
from tgf.data.database import Database


router = APIRouter()


def get_pid_file(config: Config) -> Path:
    """Get path to PID file"""
    return config.data_dir / "tgf-watch.pid"


def get_log_file(config: Config) -> Path:
    """Get path to daemon log file"""
    return config.logs_dir / "watch.log"


def is_process_running(pid: int) -> bool:
    """Check if a process with given PID is running"""
    try:
        os.kill(pid, 0)
        return True
    except (OSError, ProcessLookupError):
        return False


def read_pid(config: Config) -> int | None:
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


def write_pid(config: Config, pid: int):
    """Write PID to file"""
    get_pid_file(config).write_text(str(pid))


def remove_pid(config: Config):
    """Remove PID file"""
    pid_file = get_pid_file(config)
    if pid_file.exists():
        pid_file.unlink()


@router.get("/status", response_model=WatcherStatus)
async def get_watcher_status(
    config: Config = Depends(get_api_config),
    db: Database = Depends(get_db),
    _: str = Depends(get_current_user)
):
    """Get watcher status"""
    pid = read_pid(config)
    log_file = get_log_file(config)
    
    # Get rule counts
    all_rules = await db.get_all_rules()
    enabled_rules = await db.get_all_rules(enabled_only=True)
    
    return WatcherStatus(
        running=pid is not None,
        pid=pid,
        log_file=str(log_file) if log_file.exists() else None,
        rules_count=len(all_rules),
        enabled_rules=len(enabled_rules)
    )


@router.post("/start", response_model=MessageResponse)
async def start_watcher(
    rule_name: str = None,
    config: Config = Depends(get_api_config),
    _: str = Depends(get_current_user)
):
    """Start watcher in background"""
    # Check if already running
    existing_pid = read_pid(config)
    if existing_pid:
        raise HTTPException(
            status_code=409,
            detail=f"Watcher already running (PID: {existing_pid})"
        )
    
    # Build command - detect if running from PyInstaller bundle
    if getattr(sys, 'frozen', False):
        executable = sys.executable
        cmd = [executable, '-n', 'default', 'watch']
    else:
        cmd = [sys.executable, '-m', 'tgf', '-n', 'default', 'watch']
    
    if rule_name:
        cmd.append(rule_name)
    
    # Log file
    log_file = get_log_file(config)
    log_file.parent.mkdir(parents=True, exist_ok=True)
    
    # Start process
    if sys.platform == 'win32':
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
    
    write_pid(config, pid)
    
    return MessageResponse(message=f"Watcher started (PID: {pid})")


@router.post("/stop", response_model=MessageResponse)
async def stop_watcher(
    config: Config = Depends(get_api_config),
    _: str = Depends(get_current_user)
):
    """Stop watcher"""
    pid = read_pid(config)
    if pid is None:
        raise HTTPException(
            status_code=404,
            detail="Watcher is not running"
        )
    
    try:
        if sys.platform == 'win32':
            subprocess.run(['taskkill', '/F', '/PID', str(pid)], capture_output=True)
        else:
            os.kill(pid, signal.SIGTERM)
        
        remove_pid(config)
        return MessageResponse(message=f"Watcher stopped (PID: {pid})")
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to stop watcher: {e}"
        )


@router.get("/logs", response_model=LogsResponse)
async def get_logs(
    lines: int = 100,
    config: Config = Depends(get_api_config),
    _: str = Depends(get_current_user)
):
    """Get recent log entries"""
    log_file = get_log_file(config)
    
    if not log_file.exists():
        return LogsResponse(logs=[], total=0)
    
    # Read last N lines
    try:
        with open(log_file, 'r', encoding='utf-8', errors='ignore') as f:
            all_lines = f.readlines()
        
        recent_lines = all_lines[-lines:] if len(all_lines) > lines else all_lines
        
        logs = []
        for line in recent_lines:
            line = line.strip()
            if not line:
                continue
            
            # Parse log line: "2026-01-31 10:00:00 [INFO] module: message"
            parts = line.split(' ', 3)
            if len(parts) >= 4:
                timestamp = f"{parts[0]} {parts[1]}"
                level = parts[2].strip('[]')
                message = parts[3] if len(parts) > 3 else ""
            else:
                timestamp = ""
                level = "INFO"
                message = line
            
            logs.append(LogEntry(
                timestamp=timestamp,
                level=level,
                message=message
            ))
        
        return LogsResponse(logs=logs, total=len(all_lines))
    
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to read logs: {e}"
        )
