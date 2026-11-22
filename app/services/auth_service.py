import uuid
from typing import Optional, Tuple
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import HTTPException, status
from app.repositories.user_repo import UserRepository
from app.core.security import verify_password, create_access_token, create_refresh_token, decode_token
from app.services.firebase import firebase_service
from app.models.users import User
from app.schemas.v1.auth import Token

class AuthService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.user_repo = UserRepository(db)

    async def authenticate_user(self, identifier: str, password: str) -> Optional[User]:
        user = await self.user_repo.get_by_email(identifier)
        if not user:
            user = await self.user_repo.get_by_username(identifier)
        if not user or not verify_password(password, user.hashed_password):
            return None
        return user

    def generate_tokens(self, user: User) -> Token:
        access_token = create_access_token(subject=str(user.id), claims={"email": user.email, "is_admin": user.is_admin})
        refresh_token = create_refresh_token(subject=str(user.id))
        return Token(access_token=access_token, refresh_token=refresh_token, token_type="bearer")

    async def refresh_access_token(self, token_str: str) -> Token:
        payload = decode_token(token_str)
        if not payload or payload.get("type") != "refresh":
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid refresh token")
        user_id = payload.get("sub")
        user = await self.user_repo.get_by_id(uuid.UUID(user_id))
        if not user or not user.is_active:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found or inactive")
        return self.generate_tokens(user)

    async def login_with_firebase(self, id_token: str) -> Tuple[User, Token]:
        decoded = firebase_service.verify_token(id_token)
        user = await firebase_service.authenticate_or_sync_firebase_user(self.db, decoded)
        tokens = self.generate_tokens(user)
        return user, tokens
