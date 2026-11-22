import uuid
from typing import Optional, List, Tuple
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from app.repositories.base import BaseRepository
from app.models.users import Role, User

class RBACRepository(BaseRepository[Role]):
    def __init__(self, db: AsyncSession):
        super().__init__(Role, db)

    async def get_by_name(self, name: str) -> Optional[Role]:
        stmt = select(Role).where(Role.role_name == name)
        result = await self.db.execute(stmt)
        return result.scalars().first()

    async def list_roles_with_counts(self) -> List[Tuple[Role, int]]:
        stmt = (
            select(Role, func.count(User.id).label("users_count"))
            .outerjoin(User, User.role_id == Role.id)
            .group_by(Role.id)
            .order_by(Role.role_name)
        )
        result = await self.db.execute(stmt)
        return [(row[0], row[1]) for row in result.all()]

    async def count_users_with_role(self, role_id: uuid.UUID) -> int:
        stmt = select(func.count(User.id)).where(User.role_id == role_id)
        return (await self.db.execute(stmt)).scalar_one() or 0

