"""
TGF Web API - FastAPI Backend

RESTful API for managing TGF forwarding rules and watcher.
"""

import logging
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from tgf import __version__
from tgf.data.config import get_config

from api.routers import rules, watcher, states, auth, telegram, chats, forward, backup, accounts, tasks, settings
from api.services.watcher_manager import get_watcher_manager
from api.services.task_manager import TaskManager
from api.services.telegram import TelegramService
from tgf.data.database import Database
from tgf.utils.upload_settings import load_upload_settings

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)

# Set log levels for specific modules
logging.getLogger("api.routers.chats").setLevel(logging.DEBUG)
logging.getLogger("tgf").setLevel(logging.INFO)
# Reduce noise from telethon
logging.getLogger("telethon").setLevel(logging.WARNING)

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan events"""
    # Startup
    config = get_config()
    app.state.config = config
    
    # Initialize TaskManager
    db = Database(config.db_path)
    await db.connect() # Connect temporarily to init schema if needed, or pass db instance
                  # TaskManager gets its own db/deps usually via DI, but for singleton init:
    
    # Actually TaskManager needs dependencies. 
    # Let's initialize it with fresh instances or rely on it being initialized on first use if strictly DI
    # But for background loop it needs explicit start.
    # For now, let's just expose it via DI and let the first request trigger or use a startup event if it has background loops.
    # The plan said "Initialize TaskManager on startup".
    
    tg_service = TelegramService(config)
    TaskManager.initialize(db, tg_service)
    await load_upload_settings(db)
    
    logger.info("TGF API starting up...")
    yield
    # Shutdown - stop watcher and disconnect Telegram client gracefully
    logger.info("TGF API shutting down...")
    try:
        manager = get_watcher_manager(config)
        if manager.is_running:
            await manager.stop()
    except Exception:
        pass  # Ignore errors during shutdown
    
    # Close shared DB connection used for TaskManager if we kept one
    await db.close()

    # Disconnect shared Telegram client
    try:
        tg_manager = tg_service.client_manager
        await tg_manager.disconnect()
    except Exception:
        pass  # Ignore errors during shutdown


app = FastAPI(
    title="TGF API",
    description="Telegram Forwarder Management API",
    version=__version__,
    lifespan=lifespan,
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Update for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(auth.router, prefix="/api/auth", tags=["auth"])
app.include_router(accounts.router, prefix="/api/accounts", tags=["accounts"])
app.include_router(telegram.router, prefix="/api/telegram", tags=["telegram"])
app.include_router(rules.router, prefix="/api/rules", tags=["rules"])
app.include_router(watcher.router, prefix="/api/watcher", tags=["watcher"])
app.include_router(states.router, prefix="/api/states", tags=["states"])
app.include_router(chats.router, prefix="/api/chats", tags=["chats"])
app.include_router(forward.router, prefix="/api/forward", tags=["forward"])
app.include_router(tasks.router, prefix="/api/tasks", tags=["tasks"])
app.include_router(backup.router, prefix="/api/backup", tags=["backup"])
app.include_router(settings.router, prefix="/api/settings", tags=["settings"])


@app.get("/api/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "ok", "version": __version__}


# Serve SPA frontend if dist directory exists (Production/Docker)
import os
from fastapi.responses import FileResponse

# Check for web dist directory via env var or default location
web_dist = os.environ.get("TGF_WEB_DIST", "web/dist")
web_path = Path(web_dist).resolve()

if web_path.exists() and (web_path / "index.html").exists():
    logger.info(f"Serving frontend from {web_path}")
    
    # Mount static assets (JS, CSS, images)
    app.mount("/assets", StaticFiles(directory=str(web_path / "assets")), name="assets")
    
    # Catch-all for SPA routes - return index.html
    @app.get("/{full_path:path}")
    async def serve_spa(full_path: str):
        # Allow API routes to pass through (though they should be caught above)
        if full_path.startswith("api/"):
            return {"error": "Not Found"}
            
        # Check if file exists in root (e.g. favicon.ico, manifest.json)
        file_path = web_path / full_path
        if file_path.exists() and file_path.is_file():
            return FileResponse(file_path)
            
        # Fallback to index.html for React routing
        return FileResponse(web_path / "index.html")
else:
    logger.warning(f"Frontend dist not found at {web_path}. Running in API-only mode.")
    logger.info("For development, run 'cd web && npm run dev' separately.")

