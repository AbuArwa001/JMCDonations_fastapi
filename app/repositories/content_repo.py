import uuid
from typing import Optional, List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from app.repositories.base import BaseRepository
from app.models.ratings import Rating
from app.models.core_config import AppFeature

class RatingRepository(BaseRepository[Rating]):
    def __init__(self, db: AsyncSession):
        super().__init__(Rating, db)

    async def list_for_donation(self, donation_id: uuid.UUID) -> List[Rating]:
        stmt = select(Rating).where(Rating.donation_id == donation_id).order_by(Rating.created_at.desc())
        return list((await self.db.execute(stmt)).scalars().all())

    async def get_average_rating(self, donation_id: uuid.UUID) -> float:
        stmt = select(func.avg(Rating.rating)).where(Rating.donation_id == donation_id)
        result = (await self.db.execute(stmt)).scalar_one_or_none()
        return round(float(result), 2) if result else 0.0

class FeatureRepository(BaseRepository[AppFeature]):
    def __init__(self, db: AsyncSession):
        super().__init__(AppFeature, db)

    async def get_by_name(self, name: str) -> Optional[AppFeature]:
        stmt = select(AppFeature).where(AppFeature.name == name)
        return (await self.db.execute(stmt)).scalars().first()

    async def list_all(self) -> List[AppFeature]:
        stmt = select(AppFeature).order_by(AppFeature.name)
        return list((await self.db.execute(stmt)).scalars().all())

