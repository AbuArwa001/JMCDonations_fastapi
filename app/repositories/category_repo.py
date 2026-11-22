import uuid
from typing import Optional, List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.repositories.base import BaseRepository
from app.models.categories import Category

class CategoryRepository(BaseRepository[Category]):
    def __init__(self, db: AsyncSession):
        super().__init__(Category, db)

    async def get_by_name(self, name: str) -> Optional[Category]:
        stmt = select(Category).where(Category.category_name == name)
        result = await self.db.execute(stmt)
        return result.scalars().first()

    async def list_all(self) -> List[Category]:
        stmt = select(Category).order_by(Category.category_name)
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

