"""
Parallel upload helper for Telethon.

Uploads a file in parts with configurable worker concurrency, returning
an InputFile/InputFileBig suitable for send_file.
"""

import asyncio
import hashlib
import inspect
import math
import secrets
from pathlib import Path
from typing import Optional, Callable, Awaitable, Union

from telethon.tl.functions.upload import SaveBigFilePartRequest, SaveFilePartRequest
from telethon.tl.types import InputFile, InputFileBig

ProgressCallback = Callable[[int, int], Union[Awaitable[None], None]]

MAX_PARTS = 4000
BIG_FILE_THRESHOLD = 10 * 1024 * 1024  # 10MB


async def _maybe_await(result):
    if inspect.isawaitable(result):
        await result


async def upload_file_parallel(
    client,
    file_path: Union[str, Path],
    *,
    part_size_kb: int,
    workers: int,
    progress_callback: Optional[ProgressCallback] = None,
) -> Union[InputFile, InputFileBig]:
    path = Path(file_path)
    if not path.exists():
        raise FileNotFoundError(f"File not found: {path}")

    file_size = path.stat().st_size
    if file_size <= 0:
        raise ValueError("Cannot upload empty file")

    part_size = max(1, int(part_size_kb)) * 1024
    total_parts = math.ceil(file_size / part_size)
    if total_parts > MAX_PARTS:
        raise ValueError(
            f"Too many parts ({total_parts}). Increase part size to reduce parts."
        )

    file_id = secrets.randbits(64)
    is_big = file_size > BIG_FILE_THRESHOLD
    md5 = hashlib.md5() if not is_big else None

    uploaded = 0
    progress_lock = asyncio.Lock()
    semaphore = asyncio.Semaphore(max(1, int(workers)))

    async def report_progress(delta: int) -> None:
        nonlocal uploaded
        async with progress_lock:
            uploaded += delta
            if progress_callback:
                await _maybe_await(progress_callback(uploaded, file_size))

    async def upload_part(part_index: int, payload: bytes) -> None:
        async with semaphore:
            if is_big:
                request = SaveBigFilePartRequest(
                    file_id, part_index, total_parts, payload
                )
            else:
                request = SaveFilePartRequest(file_id, part_index, payload)
            await client(request)
            await report_progress(len(payload))

    tasks = []

    with path.open("rb") as handle:
        for part_index in range(total_parts):
            chunk = handle.read(part_size)
            if not chunk:
                break
            if md5:
                md5.update(chunk)
            tasks.append(asyncio.create_task(upload_part(part_index, chunk)))

            if len(tasks) >= max(2, int(workers)) * 2:
                done, pending = await asyncio.wait(
                    tasks, return_when=asyncio.FIRST_COMPLETED
                )
                for task in done:
                    await task
                tasks = list(pending)

    if tasks:
        await asyncio.gather(*tasks)

    file_name = path.name
    if is_big:
        return InputFileBig(file_id, total_parts, file_name)

    return InputFile(file_id, total_parts, file_name, md5.hexdigest())
