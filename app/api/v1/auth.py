from fastapi import APIRouter, Depends, HTTPException, status, Request
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from datetime import datetime, timezone
import uuid
import logging

from app.db.session import get_db
from app.models.users import User
from app.schemas.users import (
    UserCreate,
    UserResponse,
    Token,
    TokenResponse,
    LoginRequest,
    FirebaseLoginRequest,
    RefreshTokenRequest,
    FCMTokenRequest,
)
from app.core.security import (
    get_password_hash,
    verify_password,
    create_access_token,
    create_refresh_token,
    decode_token,
)
from app.services.firebase import firebase_service
from app.api.dependencies.auth import get_current_active_user

logger = logging.getLogger(__name__)

router = APIRouter()

@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def register(user_in: UserCreate, db: AsyncSession = Depends(get_db)):
    """
    Register a new user with email, username, and password.
    """
    # Check if email is already taken
    email_result = await db.execute(select(User).filter(User.email == user_in.email))
    if email_result.scalars().first():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered"
        )
        
    # Check if username is already taken
    username_result = await db.execute(select(User).filter(User.username == user_in.username))
    if username_result.scalars().first():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username already taken"
        )
        
    db_user = User(
        email=user_in.email,
        username=user_in.username,
        full_name=user_in.full_name,
        phone_number=user_in.phone_number,
        fcm_token=user_in.fcm_token,
        hashed_password=get_password_hash(user_in.password),
        is_active=True,
        is_admin=False,
        ss_login=datetime.now(timezone.utc).replace(tzinfo=None)
    )
    db.add(db_user)
    await db.commit()
    await db.refresh(db_user)
    return db_user

@router.post(
    "/login",
    response_model=TokenResponse,
    openapi_extra={
        "requestBody": {
            "content": {
                "application/json": {
                    "schema": LoginRequest.model_json_schema()
                },
                "application/x-www-form-urlencoded": {
                    "schema": LoginRequest.model_json_schema()
                }
            }
        }
    }
)
async def login(request: Request, db: AsyncSession = Depends(get_db)):
    """
    Standard login using email or username and password.
    Supports both JSON and application/x-www-form-urlencoded payloads.
    """
    content_type = request.headers.get("content-type", "")
    if "application/x-www-form-urlencoded" in content_type or "multipart/form-data" in content_type:
        form = await request.form()
        email = form.get("email")
        username = form.get("username")
        password = form.get("password")
    else:
        try:
            body = await request.json()
        except Exception:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid request body"
            )
        email = body.get("email")
        username = body.get("username")
        password = body.get("password")

    identifier = email or username
    if not identifier or not password:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email or username, and password must be provided"
        )
        
    result = await db.execute(
        select(User).filter((User.email == identifier) | (User.username == identifier))
    )
    user = result.scalars().first()
    
    if not user or not verify_password(str(password), user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email/username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
        
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Inactive user"
        )
        
    user.ss_login = datetime.now(timezone.utc).replace(tzinfo=None)
    await db.commit()
    await db.refresh(user)
    
    access_token = create_access_token(user.id)
    refresh_token = create_refresh_token(user.id)
    
    return TokenResponse(
        access_token=access_token,
        token_type="bearer",
        refresh_token=refresh_token,
        user=user
    )

@router.post("/token", response_model=Token)
async def login_access_token(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: AsyncSession = Depends(get_db)
):
    """
    OAuth2 compatible token login, used by Swagger UI 'Authorize' button.
    Accepts form-data: username (can be email or username) & password.
    """
    result = await db.execute(
        select(User).filter((User.email == form_data.username) | (User.username == form_data.username))
    )
    user = result.scalars().first()
    
    if not user or not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
        
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Inactive user"
        )
        
    user_id = user.id
    user.ss_login = datetime.now(timezone.utc).replace(tzinfo=None)
    await db.commit()
    
    access_token = create_access_token(user_id)
    refresh_token = create_refresh_token(user_id)
    
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "refresh_token": refresh_token
    }

@router.post("/firebase-login", response_model=TokenResponse)
async def firebase_login(
    payload: FirebaseLoginRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    Accepts a Firebase ID Token, verifies it, creates/syncs the local user,
    and returns internal access + refresh tokens and user profile.
    Matches FirebaseLoginView from JMCDonations Django app.
    """
    # Verify the Firebase ID token
    decoded_token = firebase_service.verify_token(payload.id_token)
    
    # Sync or create user locally
    user = await firebase_service.authenticate_or_sync_firebase_user(db, decoded_token)
    
    # Generate system JWTs
    access_token = create_access_token(user.id)
    refresh_token = create_refresh_token(user.id)
    
    return TokenResponse(
        access_token=access_token,
        token_type="bearer",
        refresh_token=refresh_token,
        user=user
    )

@router.post("/refresh", response_model=Token)
async def refresh_token(
    payload: RefreshTokenRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    Exchange a valid refresh token for a new access token.
    """
    token_data = decode_token(payload.refresh_token)
    if not token_data or token_data.get("type") != "refresh":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired refresh token",
            headers={"WWW-Authenticate": "Bearer"},
        )
        
    user_id_str = token_data.get("sub")
    if not user_id_str:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token subject",
            headers={"WWW-Authenticate": "Bearer"},
        )
        
    try:
        user_uuid = uuid.UUID(str(user_id_str))
        result = await db.execute(select(User).filter(User.id == user_uuid))
        user = result.scalars().first()
    except ValueError:
        result = await db.execute(
            select(User).filter((User.email == user_id_str) | (User.username == user_id_str))
        )
        user = result.scalars().first()
        
    if not user or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found or inactive",
            headers={"WWW-Authenticate": "Bearer"},
        )
        
    new_access_token = create_access_token(user.id)
    new_refresh_token = create_refresh_token(user.id)
    
    return {
        "access_token": new_access_token,
        "token_type": "bearer",
        "refresh_token": new_refresh_token
    }

@router.get("/me", response_model=UserResponse)
async def get_my_profile(
    current_user: User = Depends(get_current_active_user)
):
    """
    Get authenticated user's profile.
    Accepts internal JWT or direct Firebase ID token.
    """
    return current_user

@router.post("/fcm-token")
async def update_fcm_token(
    payload: FCMTokenRequest,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Update Firebase Cloud Messaging (FCM) token for notifications.
    """
    current_user.fcm_token = payload.fcm_token
    await db.commit()
    await db.refresh(current_user)
    return {
        "status": "success",
        "message": "FCM token updated",
        "user_id": str(current_user.id),
        "fcm_token": current_user.fcm_token
    }
