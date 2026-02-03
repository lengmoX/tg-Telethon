
import asyncio
import logging
import json
import uuid
import traceback
from datetime import datetime
from typing import Dict, Optional, Any
from pathlib import Path

from api.services.telegram import TelegramService
from tgf.data.database import Database
from tgf.utils.m3u8 import M3u8Downloader
from tgf.utils.upload_settings import get_upload_settings, get_upload_semaphore

logger = logging.getLogger(__name__)

class TaskManager:
    _instance = None
    
    def __init__(self, db: Database, telegram_service: TelegramService):
        self.db = db
        self.telegram = telegram_service
        self.downloader = M3u8Downloader()
        self.active_tasks: Dict[int, asyncio.Task] = {}
        self.cancel_events: Dict[int, asyncio.Event] = {}
        
    @classmethod
    def initialize(cls, db: Database, telegram_service: TelegramService):
        cls._instance = cls(db, telegram_service)
        return cls._instance
        
    @classmethod
    def get_instance(cls):
        if not cls._instance:
            raise RuntimeError("TaskManager not initialized")
        return cls._instance

    async def submit_m3u8_task(self, url: str, dest: str, filename: Optional[str] = None, caption: Optional[str] = None) -> int:
        """Submit a new M3U8 forward task"""
        # Default filename if not provided
        if not filename:
            # Generate a unique filename using timestamp and short UUID
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            short_id = str(uuid.uuid4())[:8]
            filename = f"video_{timestamp}_{short_id}"
            
        details = json.dumps({
            "url": url,
            "dest": dest,
            "filename": filename,
            "caption": caption
        })
        
        task_id = await self.db.create_task("m3u8", details)
        
        # Start background task
        loop = asyncio.get_event_loop()
        task = loop.create_task(self._run_m3u8_task(task_id, url, dest, filename, caption))
        self.active_tasks[task_id] = task
        self.cancel_events[task_id] = asyncio.Event()
        
        return task_id

    async def retry_task(self, task_id: int) -> bool:
        """Retry a failed or completed task"""
        task_data = await self.db.get_task(task_id)
        if not task_data:
            return False
            
        # Cancel if running
        if task_data['status'] in ('running', 'pending'):
            await self.cancel_task(task_data['id'])
            
        details = json.loads(task_data['details'])
        
        # Reset task state
        await self.db.update_task(
            task_id, 
            status="pending", 
            progress=0, 
            stage="init", 
            error=None
        )
        
        # Re-queue
        loop = asyncio.get_event_loop()
        if task_data['type'] == 'm3u8':
            task = loop.create_task(self._run_m3u8_task(
                task_id, 
                details['url'], 
                details['dest'], 
                details.get('filename'), 
                details.get('caption')
            ))
            self.active_tasks[task_id] = task
            self.cancel_events[task_id] = asyncio.Event()
            return True
            
        return False

    async def cancel_task(self, task_id: int) -> bool:
        """Cancel a running task"""
        if task_id in self.cancel_events:
            self.cancel_events[task_id].set()
            
        if task_id in self.active_tasks:
            self.active_tasks[task_id].cancel()
            try:
                await self.active_tasks[task_id]
            except asyncio.CancelledError:
                pass
            del self.active_tasks[task_id]
            
        if task_id in self.cancel_events:
            del self.cancel_events[task_id]
            
        await self.db.update_task(task_id, status="cancelled", stage="cancelled")
        return True

    async def delete_task_data(self, task_id: int) -> bool:
        """Delete task and cleanup files"""
        await self.cancel_task(task_id)
        
        # Cleanup files if any persisted (though usually cleaned up after run)
        # Note: We don't store file path permanently unless successful, but temp files might exist.
        # Ideally, _run_m3u8_task cleans up. Here we just delete DB entry.
        return await self.db.delete_task(task_id)

    async def _run_m3u8_task(self, task_id: int, url: str, dest: str, filename: str, caption: Optional[str]):
        """Execute M3U8 download and forward"""
        try:
            await self.db.update_task(task_id, status="running", stage="downloading", progress=0)
            
            # 1. Download
            async def report_download_progress(percent: float):
                # Update DB every 1% or so to avoid spamming? 
                # For now update every callback but maybe throttle in real implementation
                await self.db.update_task(task_id, progress=percent)

            cancel_event = self.cancel_events.get(task_id)
            
            file_path = await self.downloader.download(
                url, 
                filename, 
                progress_callback=report_download_progress,
                cancel_event=cancel_event
            )
            
            if cancel_event and cancel_event.is_set():
                await self.db.update_task(task_id, status="cancelled", stage="cancelled")
                return

            if not file_path:
                raise Exception("Download failed (file not created)")

            # Check file size
            file_size = file_path.stat().st_size
            if file_size == 0:
                raise Exception("Downloaded file is empty")

            await self.db.update_task(task_id, stage="uploading", progress=0)
            
            # 2. Upload
            async def report_upload_progress(current, total):
                if total > 0:
                    percent = (current / total) * 100
                    await self.db.update_task(task_id, progress=percent)
            
            client = await self.telegram.get_client()
            if not client:
                raise Exception("Telegram client not connected")

            # Resolve destination
            try:
                entity = await client.get_input_entity(dest) if dest != "me" else "me"
            except ValueError:
                if dest.isdigit():
                    entity = await client.get_input_entity(int(dest))
                else:
                    entity = await client.get_input_entity(dest)

            settings = get_upload_settings()
            upload_semaphore = get_upload_semaphore()

            # Send file using parallel upload with global concurrency limit
            async with upload_semaphore:
                input_file = await client.upload_file_parallel(
                    file_path,
                    part_size_kb=settings.part_size_kb,
                    workers=settings.threads,
                    progress_callback=report_upload_progress,
                )
                await client.send_file(
                    entity,
                    input_file,
                    caption=caption if caption else None,
                    supports_streaming=True,
                )
            
            # 3. Cleanup & Finish
            self.downloader.cleanup(file_path)
            await self.db.update_task(task_id, status="completed", stage="done", progress=100)
            
        except asyncio.CancelledError:
            logger.info(f"Task {task_id} cancelled")
            await self.db.update_task(task_id, status="cancelled", stage="cancelled")
        except Exception as e:
            logger.error(f"Task {task_id} failed: {e}", exc_info=True)
            await self.db.update_task(task_id, status="failed", error=str(e))
        finally:
            # Cleanup cleanup
            if task_id in self.active_tasks:
                del self.active_tasks[task_id]
            if task_id in self.cancel_events:
                del self.cancel_events[task_id]
