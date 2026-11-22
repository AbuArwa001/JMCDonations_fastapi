from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession
from app.api.deps import get_db, get_current_user
from app.services.auth_service import AuthService
from app.services.user_service import get_user_response
from app.models.users import User
from app.core.security import get_password_hash, verify_password
from app.schemas.v1.auth import (
    Token, LoginRequest, FirebaseLoginRequest, RefreshTokenRequest,
    PasswordChangeRequest, ForgotPasswordRequest, ResetPasswordRequest
)
from app.schemas.v1.users import UserCreate, TokenResponse, UserResponse
from app.schemas.common import MessageResponse

router = APIRouter()

@router.post("/token", response_model=Token)
async def login_for_access_token(form_data: OAuth2PasswordRequestForm = Depends(), db: AsyncSession = Depends(get_db)):
    service = AuthService(db)
    user = await service.authenticate_user(form_data.username, form_data.password)
    if not user:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Incorrect username or password")
    return service.generate_tokens(user)

@router.post("/login", response_model=TokenResponse)
async def login(credentials: LoginRequest, db: AsyncSession = Depends(get_db)):
    service = AuthService(db)
    ident = credentials.email_or_username or credentials.email or credentials.username or ""
    user = await service.authenticate_user(ident, credentials.password)
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid email or password")
    tokens = service.generate_tokens(user)
    u_resp = await get_user_response(db, user)
    return TokenResponse(access_token=tokens.access_token, refresh_token=tokens.refresh_token, user=u_resp)

@router.post("/firebase-login", response_model=TokenResponse)
async def firebase_login(req: FirebaseLoginRequest, db: AsyncSession = Depends(get_db)):
    service = AuthService(db)
    user, tokens = await service.login_with_firebase(req.id_token)
    u_resp = await get_user_response(db, user)
    return TokenResponse(access_token=tokens.access_token, refresh_token=tokens.refresh_token, user=u_resp)

@router.post("/refresh", response_model=Token)
async def refresh_token(req: RefreshTokenRequest, db: AsyncSession = Depends(get_db)):
    service = AuthService(db)
    return await service.refresh_access_token(req.refresh_token)

@router.post("/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
async def register(user_in: UserCreate, db: AsyncSession = Depends(get_db)):
    service = AuthService(db)
    if await service.user_repo.get_by_email(user_in.email):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Email already registered")
    if await service.user_repo.get_by_username(user_in.username):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Username already taken")
    user = User(
        email=user_in.email, username=user_in.username, full_name=user_in.full_name,
        phone_number=user_in.phone_number, hashed_password=get_password_hash(user_in.password),
        is_active=True, is_admin=False
    )
    created = await service.user_repo.create(user)
    await db.commit()
    tokens = service.generate_tokens(created)
    u_resp = await get_user_response(db, created)
    return TokenResponse(access_token=tokens.access_token, refresh_token=tokens.refresh_token, user=u_resp)

@router.post("/change-password", response_model=MessageResponse)
async def change_password(req: PasswordChangeRequest, current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    if not verify_password(req.old_password, current_user.hashed_password):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Current password is incorrect")
    current_user.hashed_password = get_password_hash(req.new_password)
    await db.commit()
    return MessageResponse(message="Password changed successfully")

@router.post("/logout", response_model=MessageResponse)
async def logout():
    return MessageResponse(message="Logged out successfully")
