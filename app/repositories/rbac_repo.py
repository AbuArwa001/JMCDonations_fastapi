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
        roles = list((await self.db.execute(select(Role).order_by(Role.role_name))).scalars().all())
        counts_res = await self.db.execute(
            select(User.role_id, func.count(User.id))
            .where(User.role_id.is_not(None))
            .group_by(User.role_id)
        )
        counts = {r[0]: r[1] for r in counts_res.all()}
        return [(r, counts.get(r.id, 0)) for r in roles]

    async def count_users_with_role(self, role_id: uuid.UUID) -> int:
        stmt = select(func.count(User.id)).where(User.role_id == role_id)
        return (await self.db.execute(stmt)).scalar_one() or 0

