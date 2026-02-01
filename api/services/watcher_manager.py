"""
Watcher Manager - Manages background watcher task integrated into FastAPI

This service wraps WatchService and runs it as an asyncio background task,
eliminating the need to spawn separate processes.
"""

import asyncio
from datetime import datetime
from typing import Optional, List, Callable
from dataclasses import dataclass, field

from tgf.service.watch_service import WatchService, SyncResult
from tgf.data.config import Config, get_config
from tgf.utils.logger import get_logger


logger = get_logger(__name__)


@dataclass
class WatcherState:
    """Current state of the watcher"""
    running: bool = False
    started_at: Optional[datetime] = None
    last_sync_at: Optional[datetime] = None
    sync_count: int = 0
    last_results: List[SyncResult] = field(default_factory=list)
    error: Optional[str] = None


class WatcherManager:
    """
    Singleton manager for the background watcher task.
    
    Integrates WatchService into FastAPI as an asyncio background task,
    avoiding subprocess spawning and window popup issues on Windows.
    """
    
    _instance: Optional["WatcherManager"] = None
    
    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self, config: Optional[Config] = None, namespace: str = "default"):
        if self._initialized:
            return
        
        self._config = config or get_config()
        self._namespace = namespace
        self._watch_service: Optional[WatchService] = None
        self._task: Optional[asyncio.Task] = None
        self._state = WatcherState()
        self._stop_event = asyncio.Event()
        self._initialized = True
    
    @classmethod
    def get_instance(cls, config: Optional[Config] = None, namespace: str = "default") -> "WatcherManager":
        """Get singleton instance"""
        return cls(config, namespace)
    
    @property
    def state(self) -> WatcherState:
        """Get current watcher state"""
        return self._state
    
    @property
    def is_running(self) -> bool:
        """Check if watcher is running"""
        return self._state.running and self._task is not None and not self._task.done()
    
    async def start(self, rule_name: Optional[str] = None) -> bool:
        """
        Start the watcher as a background task.
        
        Args:
            rule_name: Optional specific rule to watch (None = all enabled rules)
            
        Returns:
            True if started successfully, False if already running
        """
        if self.is_running:
            logger.warning("Watcher already running")
            return False
        
        # Reset state
        self._state = WatcherState(running=True, started_at=datetime.now())
        self._stop_event.clear()
        
        # Create and start background task
        self._task = asyncio.create_task(
            self._watch_loop(rule_name),
            name="watcher_background_task"
        )
        
        logger.info("Watcher started as background task")
        return True
    
    async def stop(self) -> bool:
        """
        Stop the watcher background task.
        
        Returns:
            True if stopped successfully, False if not running
        """
        if not self.is_running:
            logger.warning("Watcher not running")
            return False
        
        # Signal stop
        self._stop_event.set()
        
        # Stop the watch service
        if self._watch_service:
            self._watch_service.stop()
        
        # Wait for task to complete with timeout
        if self._task:
            try:
                await asyncio.wait_for(self._task, timeout=10.0)
            except asyncio.TimeoutError:
                logger.warning("Watcher task did not stop gracefully, cancelling")
                self._task.cancel()
                try:
                    await self._task
                except asyncio.CancelledError:
                    pass
        
        self._state.running = False
        logger.info("Watcher stopped")
        return True
    
    async def _watch_loop(self, rule_name: Optional[str] = None):
        """
        Main watch loop that runs in background.
        
        This wraps WatchService.watch() and handles:
        - Connection management
        - Error recovery
        - State tracking
        """
        try:
            # Create watch service
            self._watch_service = WatchService(
                config=self._config,
                namespace=self._namespace
            )
            
            # Connect
            await self._watch_service.connect()
            logger.info("Watch service connected")
            
            # Define callback for sync results
            def on_sync(results: List[SyncResult]):
                self._state.last_sync_at = datetime.now()
                self._state.sync_count += 1
                self._state.last_results = results
                
                # Log summary
                total_forwarded = sum(r.messages_forwarded for r in results)
                if total_forwarded > 0:
                    logger.info(f"Sync cycle {self._state.sync_count}: {total_forwarded} messages forwarded")
            
            # Run watch loop - this blocks until stopped
            await self._watch_service.watch(
                rule_name=rule_name,
                on_sync=on_sync
            )
            
        except asyncio.CancelledError:
            logger.info("Watcher task cancelled")
            raise
        except Exception as e:
            logger.error(f"Watcher error: {e}")
            self._state.error = str(e)
            self._state.running = False
        finally:
            # Cleanup
            if self._watch_service:
                try:
                    await self._watch_service.disconnect()
                except Exception as e:
                    logger.error(f"Error disconnecting watch service: {e}")
            self._watch_service = None
            self._state.running = False
    
    async def get_status(self) -> dict:
        """Get detailed watcher status"""
        return {
            "running": self.is_running,
            "started_at": self._state.started_at.isoformat() if self._state.started_at else None,
            "last_sync_at": self._state.last_sync_at.isoformat() if self._state.last_sync_at else None,
            "sync_count": self._state.sync_count,
            "error": self._state.error,
            "last_results": [
                {
                    "rule_name": r.rule_name,
                    "messages_found": r.messages_found,
                    "messages_forwarded": r.messages_forwarded,
                    "messages_failed": r.messages_failed,
                    "error": r.error
                }
                for r in self._state.last_results
            ]
        }


# Global instance accessor
def get_watcher_manager(config: Optional[Config] = None, namespace: str = "default") -> WatcherManager:
    """Get the global watcher manager instance"""
    return WatcherManager.get_instance(config, namespace)
