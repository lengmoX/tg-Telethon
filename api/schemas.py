"""
Pydantic schemas for API request/response models
"""

from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field


# ============== Auth ==============

class LoginRequest(BaseModel):
    username: str = "admin"  # Default for compatibility, but now required
    password: str

class UserCreate(BaseModel):
    username: str
    password: str

class AuthStatus(BaseModel):
    initialized: bool  # True if at least one user exists
    need_setup: bool   # Alias for not initialized


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


# ============== Rules ==============

class RuleCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=50)
    source_chat: str = Field(..., description="Source chat ID or username")
    target_chat: str = Field(..., description="Target chat ID or username")
    mode: str = Field(default="clone", pattern="^(clone|direct)$")
    interval_min: int = Field(default=30, ge=1, le=1440)
    filter_text: Optional[str] = None
    enabled: bool = True


class RuleUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=50)
    source_chat: Optional[str] = None
    target_chat: Optional[str] = None
    mode: Optional[str] = Field(None, pattern="^(clone|direct)$")
    interval_min: Optional[int] = Field(None, ge=1, le=1440)
    filter_text: Optional[str] = None
    enabled: Optional[bool] = None


class RuleResponse(BaseModel):
    id: int
    name: str
    source_chat: str
    target_chat: str
    mode: str
    interval_min: int
    filter_text: Optional[str]
    enabled: bool
    created_at: Optional[str]
    updated_at: Optional[str]


# ============== States ==============

class StateResponse(BaseModel):
    rule_id: int
    rule_name: str
    namespace: str
    last_msg_id: int
    total_forwarded: int
    last_sync_at: Optional[str]


# ============== Watcher ==============

class WatcherStatus(BaseModel):
    running: bool
    pid: Optional[int]
    log_file: Optional[str]
    rules_count: int
    enabled_rules: int


class LogEntry(BaseModel):
    timestamp: str
    level: str
    message: str


class LogsResponse(BaseModel):
    logs: List[LogEntry]
    total: int


# ============== Telegram Auth ==============

class TelegramUser(BaseModel):
    id: int
    username: Optional[str]
    first_name: Optional[str]
    last_name: Optional[str]
    phone: Optional[str]
    is_premium: bool = False


class TelegramAuthStatus(BaseModel):
    logged_in: bool
    state: str = Field(..., description="Current auth state: IDLE, QR_READY, WAITING_PASSWORD, SUCCESS, FAILED")
    qr_url: Optional[str] = None
    user: Optional[TelegramUser] = None
    error: Optional[str] = None


class TelegramPasswordRequest(BaseModel):
    password: str


# ============== Chats ==============

class ChatInfo(BaseModel):
    """Chat/Dialog information"""
    id: int
    name: str
    type: str = Field(..., description="user, group, or channel")
    username: Optional[str] = None
    unread_count: int = 0
    last_message_date: Optional[str] = None


class ChatListResponse(BaseModel):
    """Response for chat list"""
    chats: List[ChatInfo]
    total: int


class ExportRequest(BaseModel):
    """Request to export messages from a chat"""
    chat: str = Field(..., description="Chat ID, username, or link")
    limit: Optional[int] = Field(None, ge=1, le=10000, description="Max messages to export")
    from_id: int = Field(0, ge=0, description="Start from message ID")
    to_id: int = Field(0, ge=0, description="End at message ID")
    msg_type: str = Field("all", pattern="^(all|media|text|photo|video|document)$")
    with_content: bool = Field(False, description="Include message text content")


class ExportResponse(BaseModel):
    """Response for export operation"""
    success: bool
    message_count: int
    chat_name: str
    chat_username: Optional[str] = None
    chat_id: int
    links: List[str] = Field(default_factory=list, description="Message links in format https://t.me/chat/id")


# ============== Forward ==============

class ForwardRequest(BaseModel):
    """Request to forward messages"""
    links: List[str] = Field(..., min_length=1, description="Message links to forward")
    dest: str = Field("me", description="Destination chat (me, @username, or chat_id)")
    mode: str = Field("clone", pattern="^(clone|direct)$", description="Forward mode")
    detect_album: bool = Field(True, description="Auto-detect and forward albums together")


class ForwardResultItem(BaseModel):
    """Result of a single forward operation"""
    link: str
    success: bool
    error: Optional[str] = None
    target_msg_id: Optional[int] = None


class ForwardResponse(BaseModel):
    """Response for forward operation"""
    success: bool
    total: int
    succeeded: int
    failed: int
    results: List[ForwardResultItem]


# ============== Common ==============

class MessageResponse(BaseModel):
    message: str
    success: bool = True


class ErrorResponse(BaseModel):
    success: bool = False


# ============== M3U8 ==============

class M3u8ForwardRequest(BaseModel):
    """Request to download and forward M3U8 stream"""
    url: str = Field(..., description="M3U8 URL")
    dest: str = Field("me", description="Destination chat (me, @username, or chat_id)")
    filename: Optional[str] = Field(None, description="Custom filename (optional)")
    caption: Optional[str] = Field(None, description="Caption for video")


class M3u8ForwardResponse(BaseModel):
    """Response for M3U8 forward operation"""
    success: bool
    status: str
    task_id: int
    error: Optional[str] = None


# ============== Tasks ==============

class TaskResponse(BaseModel):
    """Response for task details"""
    id: int
    type: str
    status: str
    progress: float
    stage: Optional[str] = None
    details: Optional[str] = None
    error: Optional[str] = None
    created_at: Optional[str]
    updated_at: Optional[str]

class TaskListResponse(BaseModel):
    """List of tasks"""
    tasks: List[TaskResponse]
    total: int


# ============== Upload Settings ==============

class UploadSettings(BaseModel):
    """Upload settings for parallel/concurrent uploads"""
    threads: int = Field(..., ge=1, le=32, description="Workers per upload")
    limit: int = Field(..., ge=1, le=8, description="Max concurrent uploads")
    part_size_kb: int = Field(..., ge=1, le=512, description="Part size in KB")


class UploadSettingsUpdate(BaseModel):
    """Partial update for upload settings"""
    threads: Optional[int] = Field(None, ge=1, le=32)
    limit: Optional[int] = Field(None, ge=1, le=8)
    part_size_kb: Optional[int] = Field(None, ge=1, le=512)

