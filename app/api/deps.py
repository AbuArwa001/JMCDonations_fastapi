import uuid
from typing import Optional, Set
from fastapi import Depends, HTTPException, status, Query
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.core.config import settings
from app.core.security import decode_token
from app.core.database import get_db
from app.models.users import User, Role
from app.core.permissions import WILDCARD
from app.services.firebase import firebase_service
from app.schemas.common import PaginationParams

oauth2_scheme = OAuth2PasswordBearer(tokenUrl=f"{settings.API_V1_STR}/auth/token", auto_error=False)

async def get_current_user(token: Optional[str] = Depends(oauth2_scheme), db: AsyncSession = Depends(get_db)) -> User:
    if not token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated", headers={"WWW-Authenticate": "Bearer"})
    user: Optional[User] = None
    payload = decode_token(token)
    if payload:
        if payload.get("type") and payload.get("type") != "access":
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token type")
        sub = payload.get("sub")
        if sub:
            try:
                user = await db.get(User, uuid.UUID(str(sub)))
            except ValueError:
                res = await db.execute(select(User).filter((User.email == sub) | (User.username == sub)))
                user = res.scalars().first()
    if not user:
        try:
            decoded = firebase_service.verify_token(token)
            if decoded:
                user = await firebase_service.authenticate_or_sync_firebase_user(db, decoded)
        except Exception:
            pass
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Could not validate credentials")
    if not user.is_active:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Inactive user")
    return user

async def get_current_active_user(current_user: User = Depends(get_current_user)) -> User:
    return current_user

async def get_current_admin_user(current_user: User = Depends(get_current_active_user)) -> User:
    if not current_user.is_admin:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin privileges required")
    return current_user

async def get_optional_current_user(token: Optional[str] = Depends(oauth2_scheme), db: AsyncSession = Depends(get_db)) -> Optional[User]:
    if not token:
        return None
    try:
        return await get_current_user(token, db)
    except Exception:
        return None

async def get_user_permissions(db: AsyncSession, user: User) -> Set[str]:
    if not user.is_admin or not user.is_active:
        return set()
    if not user.role_id:
        return {WILDCARD}
    role = await db.get(Role, user.role_id)
    return set(role.permissions or []) if role else {WILDCARD}

def require_permission(*perms: str):
    async def _checker(current_user: User = Depends(get_current_admin_user), db: AsyncSession = Depends(get_db)) -> User:
        granted = await get_user_permissions(db, current_user)
        if WILDCARD not in granted and not any(p in granted for p in perms):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=f"Missing permission: {' or '.join(perms)}")
        return current_user
    return _checker

async def get_current_super_admin(current_user: User = Depends(get_current_admin_user), db: AsyncSession = Depends(get_db)) -> User:
    granted = await get_user_permissions(db, current_user)
    if WILDCARD not in granted:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Super Admin privileges required")
    return current_user

def get_pagination(page: int = Query(1, ge=1), page_size: int = Query(20, ge=1, le=100)) -> PaginationParams:
    return PaginationParams(page=page, page_size=page_size)

