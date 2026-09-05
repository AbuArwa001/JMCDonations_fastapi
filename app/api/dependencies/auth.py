import uuid
import logging
from typing import Optional
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.config import settings
from app.core.security import decode_token
from app.db.session import get_db
from app.models.users import User
from app.services.firebase import firebase_service

logger = logging.getLogger(__name__)

oauth2_scheme = OAuth2PasswordBearer(
    tokenUrl=f"{settings.API_V1_STR}/auth/token",
    auto_error=False
)

async def get_current_user(
    token: Optional[str] = Depends(oauth2_scheme),
    db: AsyncSession = Depends(get_db)
) -> User:
    """
    Authenticate request via Bearer token.
    Supports BOTH:
    1. Internal JWT access tokens (from /auth/login, /auth/token, /auth/firebase-login)
    2. Direct Firebase ID tokens (as in JMCDonations FirebaseDRFAuthentication)
    """
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user: Optional[User] = None

    # 1. Attempt decoding internal JWT
    payload = decode_token(token)
    if payload:
        token_type = payload.get("type")
        if token_type and token_type != "access":
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token type",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        user_id_str = payload.get("sub")
        if user_id_str:
            try:
                user_uuid = uuid.UUID(str(user_id_str))
                result = await db.execute(select(User).filter(User.id == user_uuid))
                user = result.scalars().first()
            except ValueError:
                result = await db.execute(
                    select(User).filter((User.email == user_id_str) | (User.username == user_id_str))
                )
                user = result.scalars().first()

    # 2. If not an internal JWT, attempt Firebase ID token verification
    if not user:
        try:
            decoded_firebase = firebase_service.verify_token(token)
            if decoded_firebase:
                user = await firebase_service.authenticate_or_sync_firebase_user(db, decoded_firebase)
        except HTTPException:
            # Propagate expired/invalid Firebase errors
            raise
        except Exception as e:
            logger.debug(f"Firebase token verification failed: {e}")

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Inactive user"
        )

    return user

async def get_current_active_user(
    current_user: User = Depends(get_current_user)
) -> User:
    """
    Ensure the authenticated user is active.
    """
    if not current_user.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Inactive user"
        )
    return current_user

async def get_current_admin_user(
    current_user: User = Depends(get_current_active_user)
) -> User:
    """
    Ensure the authenticated user has admin privileges.
    """
    if not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="The user doesn't have enough privileges"
        )
    return current_user

async def get_optional_current_user(
    token: Optional[str] = Depends(oauth2_scheme),
    db: AsyncSession = Depends(get_db)
) -> Optional[User]:
    """
    Optionally authenticate a user if a token is present, returning None if unauthenticated.
    """
    if not token:
        return None
    try:
        return await get_current_user(token=token, db=db)
    except Exception:
        return None

