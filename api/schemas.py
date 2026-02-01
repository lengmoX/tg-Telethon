"""
Pydantic schemas for API request/response models
"""

from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field


# ============== Auth ==============

class LoginRequest(BaseModel):
    password: str


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


# ============== Common ==============

class MessageResponse(BaseModel):
    message: str
    success: bool = True


class ErrorResponse(BaseModel):
    detail: str
    success: bool = False
