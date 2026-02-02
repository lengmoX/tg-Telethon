from fastapi import APIRouter, HTTPException, status, Depends
from tgf.data.database import Database

from api.schemas import LoginRequest, TokenResponse, MessageResponse, UserCreate, AuthStatus
from api.deps import verify_password, create_token, revoke_token, get_db, get_password_hash


router = APIRouter()


@router.get("/status", response_model=AuthStatus)
async def auth_status(db: Database = Depends(get_db)):
    """Check if the system is initialized (has users)"""
    count = await db.count_users()
    return AuthStatus(
        initialized=count > 0,
        need_setup=count == 0
    )


@router.post("/setup", response_model=TokenResponse)
async def setup_admin(request: UserCreate, db: Database = Depends(get_db)):
    """
    Initialize system by creating the first admin user.
    Only allowed when no users exist.
    """
    count = await db.count_users()
    if count > 0:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="System already initialized"
        )
    
    hashed_pw = get_password_hash(request.password)
    username = request.username.strip()
    
    if not username or len(username) < 3:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username must be at least 3 characters"
        )

    await db.create_user(username, hashed_pw, is_admin=True)
    
    # Auto login
    token = create_token(username)
    return TokenResponse(access_token=token)


@router.post("/login", response_model=TokenResponse)
async def login(request: LoginRequest, db: Database = Depends(get_db)):
    """
    Login with username and password and get access token
    """
    user = await db.get_user(request.username)
    
    if not user or not verify_password(request.password, user["password_hash"]):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password"
        )
    
    token = create_token(user["username"])
    return TokenResponse(access_token=token)


@router.post("/logout", response_model=MessageResponse)
async def logout(token: str):
    """Logout and revoke token"""
    revoke_token(token)
    return MessageResponse(message="Logged out successfully")
