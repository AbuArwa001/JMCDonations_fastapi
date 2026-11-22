import uuid
from typing import Optional, List, Tuple
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, or_, func
from app.repositories.base import BaseRepository
from app.models.users import User, UserPaymentAccount, UserNotificationState

class UserRepository(BaseRepository[User]):
    def __init__(self, db: AsyncSession):
        super().__init__(User, db)

    async def get_by_email(self, email: str) -> Optional[User]:
        stmt = select(User).where(User.email == email)
        result = await self.db.execute(stmt)
        return result.scalars().first()

    async def get_by_username(self, username: str) -> Optional[User]:
        stmt = select(User).where(User.username == username)
        result = await self.db.execute(stmt)
        return result.scalars().first()

    async def get_by_firebase_uid(self, uid: str) -> Optional[User]:
        stmt = select(User).where(User.firebase_uid == uid)
        result = await self.db.execute(stmt)
        return result.scalars().first()

    async def search(self, skip: int = 0, limit: int = 20, q: Optional[str] = None, is_active: Optional[bool] = None) -> Tuple[List[User], int]:
        stmt = select(User)
        count_stmt = select(func.count(User.id))
        if q:
            cond = or_(User.email.ilike(f"%{q}%"), User.username.ilike(f"%{q}%"), User.full_name.ilike(f"%{q}%"))
            stmt = stmt.where(cond)
            count_stmt = count_stmt.where(cond)
        if is_active is not None:
            stmt = stmt.where(User.is_active == is_active)
            count_stmt = count_stmt.where(User.is_active == is_active)
        total = (await self.db.execute(count_stmt)).scalar_one() or 0
        result = await self.db.execute(stmt.offset(skip).limit(limit))
        return list(result.scalars().all()), total

    async def get_notification_state(self, user_id: uuid.UUID) -> Optional[UserNotificationState]:
        stmt = select(UserNotificationState).where(UserNotificationState.user_id == user_id)
        result = await self.db.execute(stmt)
        return result.scalars().first()

    async def get_payment_accounts(self, user_id: uuid.UUID) -> List[UserPaymentAccount]:
        stmt = select(UserPaymentAccount).where(UserPaymentAccount.user_id == user_id)
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

