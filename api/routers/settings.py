from fastapi import APIRouter, Depends

from api.deps import get_current_user, get_db
from api.schemas import UploadSettings, UploadSettingsUpdate
from tgf.data.database import Database
from tgf.utils.upload_settings import (
    apply_upload_settings,
    get_upload_settings,
    normalize_upload_settings,
    save_upload_settings,
)

router = APIRouter()


@router.get("/upload", response_model=UploadSettings)
async def get_upload_settings_endpoint(
    _: str = Depends(get_current_user),
):
    """Get current upload settings"""
    settings = get_upload_settings()
    return UploadSettings(**settings.to_dict())


@router.put("/upload", response_model=UploadSettings)
async def update_upload_settings_endpoint(
    updates: UploadSettingsUpdate,
    db: Database = Depends(get_db),
    _: str = Depends(get_current_user),
):
    """Update upload settings"""
    current = get_upload_settings()
    merged = normalize_upload_settings(
        threads=updates.threads if updates.threads is not None else current.threads,
        limit=updates.limit if updates.limit is not None else current.limit,
        part_size_kb=updates.part_size_kb if updates.part_size_kb is not None else current.part_size_kb,
    )
    apply_upload_settings(merged)
    await save_upload_settings(db, merged)
    return UploadSettings(**merged.to_dict())
