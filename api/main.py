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

from api.routers import rules, watcher, states, auth, telegram, chats
from api.services.watcher_manager import get_watcher_manager

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
    yield
    # Shutdown - stop watcher gracefully
    try:
        manager = get_watcher_manager(config)
        if manager.is_running:
            await manager.stop()
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
app.include_router(auth.router, prefix="/api/auth", tags=["认证"])
app.include_router(telegram.router, prefix="/api/telegram", tags=["Telegram 认证"])
app.include_router(rules.router, prefix="/api/rules", tags=["规则管理"])
app.include_router(watcher.router, prefix="/api/watcher", tags=["监听控制"])
app.include_router(states.router, prefix="/api/states", tags=["同步状态"])
app.include_router(chats.router, prefix="/api/chats", tags=["对话管理"])


@app.get("/api/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "ok", "version": __version__}


# NOTE: Frontend is now served separately via Vite dev server
# Run: cd web && npm run dev
# Vite proxies /api requests to this backend automatically

