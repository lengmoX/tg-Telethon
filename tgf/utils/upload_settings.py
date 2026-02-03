"""
Upload settings and runtime limits.

Provides a shared, configurable upload configuration with
global concurrency limiting for uploads.
"""

import asyncio
import logging
import os
from dataclasses import dataclass
from typing import Dict, Optional

from tgf.data.database import Database

logger = logging.getLogger(__name__)

DEFAULT_UPLOAD_THREADS = int(os.getenv("TGF_UPLOAD_THREADS", "4"))
DEFAULT_UPLOAD_LIMIT = int(os.getenv("TGF_UPLOAD_LIMIT", "2"))
DEFAULT_UPLOAD_PART_SIZE_KB = int(os.getenv("TGF_UPLOAD_PART_SIZE_KB", "256"))

MIN_UPLOAD_THREADS = 1
MAX_UPLOAD_THREADS = 32
MIN_UPLOAD_LIMIT = 1
MAX_UPLOAD_LIMIT = 8
MIN_PART_SIZE_KB = 1
MAX_PART_SIZE_KB = 512

SETTING_THREADS = "upload_threads"
SETTING_LIMIT = "upload_limit"
SETTING_PART_SIZE = "upload_part_size_kb"


@dataclass(frozen=True)
class UploadSettings:
    threads: int
    limit: int
    part_size_kb: int

    def to_dict(self) -> Dict[str, int]:
        return {
            "threads": self.threads,
            "limit": self.limit,
            "part_size_kb": self.part_size_kb,
        }


def _clamp(value: int, min_value: int, max_value: int) -> int:
    return max(min_value, min(max_value, value))


def normalize_upload_settings(
    threads: Optional[int] = None,
    limit: Optional[int] = None,
    part_size_kb: Optional[int] = None,
) -> UploadSettings:
    safe_threads = _clamp(
        int(threads) if threads is not None else DEFAULT_UPLOAD_THREADS,
        MIN_UPLOAD_THREADS,
        MAX_UPLOAD_THREADS,
    )
    safe_limit = _clamp(
        int(limit) if limit is not None else DEFAULT_UPLOAD_LIMIT,
        MIN_UPLOAD_LIMIT,
        MAX_UPLOAD_LIMIT,
    )
    safe_part_size = _clamp(
        int(part_size_kb) if part_size_kb is not None else DEFAULT_UPLOAD_PART_SIZE_KB,
        MIN_PART_SIZE_KB,
        MAX_PART_SIZE_KB,
    )
    return UploadSettings(
        threads=safe_threads,
        limit=safe_limit,
        part_size_kb=safe_part_size,
    )


_settings: UploadSettings = normalize_upload_settings()
_upload_semaphore: asyncio.Semaphore = asyncio.Semaphore(_settings.limit)


def get_upload_settings() -> UploadSettings:
    return _settings


def get_upload_semaphore() -> asyncio.Semaphore:
    return _upload_semaphore


def apply_upload_settings(settings: UploadSettings) -> None:
    global _settings, _upload_semaphore
    _settings = settings
    _upload_semaphore = asyncio.Semaphore(settings.limit)


async def load_upload_settings(db: Database) -> UploadSettings:
    values = await db.get_settings([SETTING_THREADS, SETTING_LIMIT, SETTING_PART_SIZE])
    threads = values.get(SETTING_THREADS)
    limit = values.get(SETTING_LIMIT)
    part_size = values.get(SETTING_PART_SIZE)

    def _parse_int(value: Optional[str]) -> Optional[int]:
        if value is None:
            return None
        try:
            return int(value)
        except ValueError:
            logger.warning("Invalid upload setting value: %s", value)
            return None

    settings = normalize_upload_settings(
        threads=_parse_int(threads),
        limit=_parse_int(limit),
        part_size_kb=_parse_int(part_size),
    )
    apply_upload_settings(settings)
    return settings


async def save_upload_settings(db: Database, settings: UploadSettings) -> None:
    await db.set_setting(SETTING_THREADS, str(settings.threads))
    await db.set_setting(SETTING_LIMIT, str(settings.limit))
    await db.set_setting(SETTING_PART_SIZE, str(settings.part_size_kb))
