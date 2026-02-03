
from fastapi import APIRouter, Depends, HTTPException
from typing import List

from api.deps import get_db, get_telegram_service, get_current_user
from tgf.data.database import Database
from api.services.task_manager import TaskManager
from api.schemas import TaskListResponse, TaskResponse, ErrorResponse, MessageResponse

router = APIRouter()

def get_task_manager(
    db: Database = Depends(get_db),
    telegram_service = Depends(get_telegram_service)
) -> TaskManager:
    return TaskManager.get_instance()

@router.get("", response_model=TaskListResponse)
async def get_tasks(
    limit: int = 100,
    db: Database = Depends(get_db),
    _: str = Depends(get_current_user)
):
    """List recent tasks"""
    tasks = await db.get_all_tasks(limit=limit)
    total = len(tasks) # This is approximate since we limit query
    return TaskListResponse(tasks=tasks, total=total)

@router.post("/{task_id}/retry", response_model=MessageResponse)
async def retry_task(
    task_id: int,
    manager: TaskManager = Depends(get_task_manager),
    _: str = Depends(get_current_user)
):
    """Retry a failed or cancelled task"""
    success = await manager.retry_task(task_id)
    if not success:
        raise HTTPException(status_code=400, detail="Task not found or cannot be retried")
    return MessageResponse(message="Task retried")

@router.post("/{task_id}/cancel", response_model=MessageResponse)
async def cancel_task(
    task_id: int,
    manager: TaskManager = Depends(get_task_manager),
    _: str = Depends(get_current_user)
):
    """Cancel a running task"""
    await manager.cancel_task(task_id)
    return MessageResponse(message="Task cancelled")

@router.delete("/{task_id}", response_model=MessageResponse)
async def delete_task(
    task_id: int,
    manager: TaskManager = Depends(get_task_manager),
    _: str = Depends(get_current_user)
):
    """Delete a task and its history"""
    success = await manager.delete_task_data(task_id)
    if not success:
        raise HTTPException(status_code=404, detail="Task not found")
    return MessageResponse(message="Task deleted")
