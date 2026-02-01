"""
Watcher Router - Control integrated background watcher

This router controls the WatcherManager which runs WatchService
as an asyncio background task within FastAPI.
"""

from pathlib import Path
from typing import List

from fastapi import APIRouter, Depends, HTTPException

from api.schemas import WatcherStatus, LogEntry, LogsResponse, MessageResponse
from api.deps import get_api_config, get_db, get_current_user
from api.services.watcher_manager import get_watcher_manager
from tgf.data.config import Config
from tgf.data.database import Database


router = APIRouter()


def get_log_file(config: Config) -> Path:
    """Get path to daemon log file"""
    return config.logs_dir / "watch.log"


@router.get("/status", response_model=WatcherStatus)
async def get_watcher_status(
    config: Config = Depends(get_api_config),
    db: Database = Depends(get_db),
    _: str = Depends(get_current_user)
):
    """Get watcher status"""
    manager = get_watcher_manager(config)
    log_file = get_log_file(config)
    
    # Get rule counts
    all_rules = await db.get_all_rules()
    enabled_rules = await db.get_all_rules(enabled_only=True)
    
    return WatcherStatus(
        running=manager.is_running,
        pid=None,  # No separate process anymore
        log_file=str(log_file) if log_file.exists() else None,
        rules_count=len(all_rules),
        enabled_rules=len(enabled_rules)
    )


@router.get("/status/detail")
async def get_watcher_status_detail(
    config: Config = Depends(get_api_config),
    _: str = Depends(get_current_user)
):
    """Get detailed watcher status including sync results"""
    manager = get_watcher_manager(config)
    return await manager.get_status()


@router.post("/start", response_model=MessageResponse)
async def start_watcher(
    rule_name: str = None,
    config: Config = Depends(get_api_config),
    _: str = Depends(get_current_user)
):
    """Start watcher as background task"""
    manager = get_watcher_manager(config)
    
    if manager.is_running:
        raise HTTPException(
            status_code=409,
            detail="Watcher already running"
        )
    
    success = await manager.start(rule_name=rule_name)
    
    if not success:
        raise HTTPException(
            status_code=500,
            detail="Failed to start watcher"
        )
    
    return MessageResponse(message="Watcher started as background task")


@router.post("/stop", response_model=MessageResponse)
async def stop_watcher(
    config: Config = Depends(get_api_config),
    _: str = Depends(get_current_user)
):
    """Stop watcher background task"""
    manager = get_watcher_manager(config)
    
    if not manager.is_running:
        raise HTTPException(
            status_code=404,
            detail="Watcher is not running"
        )
    
    success = await manager.stop()
    
    if not success:
        raise HTTPException(
            status_code=500,
            detail="Failed to stop watcher"
        )
    
    return MessageResponse(message="Watcher stopped")


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
