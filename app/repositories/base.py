from typing import Generic, TypeVar, Type, Optional, List, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, delete
from app.core.database import Base

ModelType = TypeVar("ModelType", bound=Base)

class BaseRepository(Generic[ModelType]):
    def __init__(self, model: Type[ModelType], db: AsyncSession):
        self.model = model
        self.db = db

    async def get_by_id(self, id: Any) -> Optional[ModelType]:
        return await self.db.get(self.model, id)

    async def get_multi(self, skip: int = 0, limit: int = 100) -> List[ModelType]:
        stmt = select(self.model).offset(skip).limit(limit)
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def count(self) -> int:
        stmt = select(func.count()).select_from(self.model)
        result = await self.db.execute(stmt)
        return result.scalar_one() or 0

    async def create(self, instance: ModelType) -> ModelType:
        self.db.add(instance)
        await self.db.flush()
        return instance

    async def update(self, instance: ModelType) -> ModelType:
        await self.db.flush()
        return instance

    async def delete(self, instance: ModelType) -> None:
        await self.db.delete(instance)
        await self.db.flush()

