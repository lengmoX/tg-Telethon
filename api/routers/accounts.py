"""
Accounts Router - Manage Telegram Accounts
"""

import asyncio
import logging
import uuid
from typing import Dict, Optional, List
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Body
from pydantic import BaseModel

from api.deps import get_db, get_current_user
from api.services.telegram_client_manager import get_telegram_client_manager
from tgf.core.client import TGClient
from tgf.data.config import get_config
from tgf.data.database import Database
from telethon.errors import SessionPasswordNeededError

logger = logging.getLogger(__name__)

router = APIRouter()

# ============ Schemas ============

class AccountInfo(BaseModel):
    id: int
    phone: Optional[str]
    session_name: str
    is_active: bool
    first_name: Optional[str]
    username: Optional[str]
    created_at: Optional[str]

class LoginInitRequest(BaseModel):
    api_id: int
    api_hash: str

class LoginStatusResponse(BaseModel):
    session_id: str
    status: str  # "waiting_qr", "scanned", "2fa_required", "logged_in", "error"
    qr_url: Optional[str] = None
    error: Optional[str] = None

class Verify2FARequest(BaseModel):
    password: str

# ============ State Management ============

class LoginSession:
    def __init__(self, api_id: int, api_hash: str):
        self.api_id = api_id
        self.api_hash = api_hash
        self.session_name = f"login_{uuid.uuid4().hex[:8]}"
        self.client = TGClient(
            config=get_config(),
            namespace=self.session_name,
            api_id=api_id,
            api_hash=api_hash
        )
        self.status = "initializing"
        self.qr_url: Optional[str] = None
        self.error: Optional[str] = None
        self.user = None
        self._task: Optional[asyncio.Task] = None
        self._qr_login = None

    async def start(self):
        try:
            self.status = "connecting"
            await self.client.connect()
            
            self._qr_login = await self.client.client.qr_login()
            self._task = asyncio.create_task(self._wait_loop())
            
        except Exception as e:
            self.status = "error"
            self.error = str(e)
            logger.error(f"Login start failed: {e}")

    async def _wait_loop(self):
        try:
            self.status = "waiting_qr"
            self.qr_url = self._qr_login.url
            
            # Wait for scan
            try:
                self.user = await self._qr_login.wait(timeout=300) # 5 min timeout
                self.status = "logged_in"
            except SessionPasswordNeededError:
                self.status = "2fa_required"
            except asyncio.TimeoutError:
                self.status = "error"
                self.error = "QR code expired"
            
        except Exception as e:
            self.status = "error"
            self.error = str(e)
            logger.error(f"Login loop failed: {e}")

    async def submit_2fa(self, password: str):
        try:
            self.user = await self.client.client.sign_in(password=password)
            self.status = "logged_in"
            return True
        except Exception as e:
            self.error = str(e)
            return False
            
    async def cleanup(self):
        if self._task:
            self._task.cancel()
        # Don't disconnect here if logged in, as we might verify credentials.
        # But actually we want to create a CLEAN session for the persistent account.
        await self.client.disconnect()


# In-memory store for pending logins
pending_logins: Dict[str, LoginSession] = {}


# ============ Endpoints ============

@router.get("", response_model=List[AccountInfo])
async def list_accounts(
    db: Database = Depends(get_db),
    _: str = Depends(get_current_user)
):
    """List all accounts"""
    accounts = await db.get_all_accounts()
    return [AccountInfo(**acc) for acc in accounts]


@router.post("/login/init", response_model=LoginStatusResponse)
async def init_login(
    request: LoginInitRequest,
    _: str = Depends(get_current_user)
):
    """Initialize login process"""
    session_id = uuid.uuid4().hex
    session = LoginSession(request.api_id, request.api_hash)
    pending_logins[session_id] = session
    
    await session.start()
    
    return LoginStatusResponse(
        session_id=session_id,
        status=session.status,
        qr_url=session.qr_url,
        error=session.error
    )


@router.get("/login/{session_id}/status", response_model=LoginStatusResponse)
async def check_login_status(
    session_id: str,
    _: str = Depends(get_current_user)
):
    """Check login status"""
    if session_id not in pending_logins:
        raise HTTPException(status_code=404, detail="Session not found")
        
    session = pending_logins[session_id]
    
    # Refresh QR URL if needed? 
    # Actually telethon qr_login.url might expire, but we handle recreation in loop?
    # For now assume static URL validity or error.
    
    return LoginStatusResponse(
        session_id=session_id,
        status=session.status,
        qr_url=session.qr_url,
        error=session.error
    )


@router.post("/login/{session_id}/2fa")
async def verify_2fa(
    session_id: str,
    request: Verify2FARequest,
    _: str = Depends(get_current_user)
):
    """Submit 2FA password"""
    if session_id not in pending_logins:
        raise HTTPException(status_code=404, detail="Session not found")
        
    session = pending_logins[session_id]
    if session.status != "2fa_required":
        raise HTTPException(status_code=400, detail="Not expecting 2FA")
        
    success = await session.submit_2fa(request.password)
    
    if not success:
        return LoginStatusResponse(
            session_id=session_id,
            status=session.status,
            error=session.error
        )
        
    return LoginStatusResponse(
        session_id=session_id,
        status="logged_in"
    )


@router.post("/login/{session_id}/confirm")
async def confirm_login(
    session_id: str,
    db: Database = Depends(get_db),
    _: str = Depends(get_current_user)
):
    """Confirm login and save account"""
    if session_id not in pending_logins:
        raise HTTPException(status_code=404, detail="Session not found")
        
    session = pending_logins[session_id]
    
    if session.status != "logged_in" or not session.user:
        raise HTTPException(status_code=400, detail="Login not complete")
    
    # Save to DB
    user = session.user
    phone = getattr(user, 'phone', None)
    username = getattr(user, 'username', None)
    first_name = getattr(user, 'first_name', None)
    
    # Generate persistent session name
    import hashlib
    session_hash = hashlib.sha256(f"{session.api_id}:{phone}:{datetime.now()}".encode()).hexdigest()[:12]
    persistent_session_name = f"acc_{session_hash}"
    
    # Create persistent session file
    # We need to export the session from the temporary client and import it?
    # TelegramClient stores session in SQLite file.
    # We can just rename the temporary session file to the persistent one!
    
    try:
        from tgf.data.session import SessionManager
        session_manager = SessionManager(get_config().sessions_dir)
        
        # Temp session path
        temp_path = session_manager.get_session_file(session.session_name)
        
        # New persistent session path
        target_path = session_manager.get_session_file(persistent_session_name)
        
        # Cleanup temp client to release file lock
        await session.cleanup()
        
        # Rename file
        if temp_path.exists():
            import shutil
            shutil.move(temp_path, target_path)
            
            # Also move journal if exists
            temp_journal = temp_path.with_suffix(".session-journal")
            if temp_journal.exists():
                shutil.move(temp_journal, target_path.with_suffix(".session-journal"))
        else:
            raise Exception("Session file not found")
            
        # Create DB entry
        account_id = await db.create_account(
            api_id=session.api_id,
            api_hash=session.api_hash,
            session_name=persistent_session_name,
            phone=phone
        )
        
        await db.update_account_info(
            account_id, 
            phone=phone,
            first_name=first_name,
            username=username
        )
        
        # Set as active if it's the first one
        accounts = await db.get_all_accounts()
        if len(accounts) == 1:
            await db.set_active_account(account_id)
            
        # Cleanup memory
        del pending_logins[session_id]
        
        # Refresh global client manager if needed
        manager = get_telegram_client_manager()
        await manager.ensure_active_account(db)
        
        return {"success": True, "account_id": account_id}
        
    except Exception as e:
        logger.error(f"Failed to save account: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to save account: {str(e)}")


@router.post("/{account_id}/activate")
async def activate_account(
    account_id: int,
    db: Database = Depends(get_db),
    _: str = Depends(get_current_user)
):
    """Switch to this account"""
    success = await db.set_active_account(account_id)
    if not success:
        raise HTTPException(status_code=404, detail="Account not found")
        
    # Switch client
    manager = get_telegram_client_manager()
    account = await db.get_account(account_id)
    
    try:
        await manager.switch_account(
            api_id=account["api_id"],
            api_hash=account["api_hash"],
            session_name=account["session_name"]
        )
    except Exception as e:
        logger.error(f"Failed to switch account: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to connect: {str(e)}")
        
    return {"success": True}


@router.delete("/{account_id}")
async def delete_account(
    account_id: int,
    db: Database = Depends(get_db),
    _: str = Depends(get_current_user)
):
    """Delete account"""
    account = await db.get_account(account_id)
    if not account:
        raise HTTPException(status_code=404, detail="Account not found")
        
    # If active, disconnect manager
    if account["is_active"]:
        manager = get_telegram_client_manager()
        await manager.disconnect()
    
    # Delete from DB
    await db.delete_account(account_id)
    
    # Delete session file
    from tgf.data.session import SessionManager
    session_manager = SessionManager(get_config().sessions_dir)
    session_manager.delete_session(account["session_name"])
    
    return {"success": True}
