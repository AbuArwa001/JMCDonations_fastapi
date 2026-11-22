import uuid
from typing import Optional, List
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import HTTPException, status
from app.repositories.community_repo import CommunityRepository
from app.models.community import CommunityContent
from app.models.bulletins import FridayBulletin
from app.models.zakat import NisabRate
from app.schemas.v1.bulletins import FridayBulletinCreate

class CommunityService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.repo = CommunityRepository(db)

    async def create_bulletin(self, data: FridayBulletinCreate) -> FridayBulletin:
        bulletin = FridayBulletin(**data.model_dump())
        self.db.add(bulletin)
        await self.db.commit()
        await self.db.refresh(bulletin)
        return bulletin

    async def update_nisab_rates(self, gold: float, silver: float, user_id: Optional[uuid.UUID] = None) -> NisabRate:
        rate = await self.repo.get_latest_nisab()
        if not rate:
            rate = NisabRate(gold_price_per_gram=gold, silver_price_per_gram=silver, updated_by_id=user_id)
            self.db.add(rate)
        else:
            rate.gold_price_per_gram = gold
            rate.silver_price_per_gram = silver
            rate.updated_by_id = user_id
        await self.db.commit()
        await self.db.refresh(rate)
        return rate

