import uuid
from typing import Optional, List
from datetime import date
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.models.bulletins import FridayBulletin
from app.models.community import CommunityContent
from app.models.duas import Dua, DuaCategory
from app.models.events import Event, EventCategory
from app.models.khutba import JumaKhutba
from app.models.zakat import NisabRate

class CommunityRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def list_bulletins(self, skip: int = 0, limit: int = 50) -> List[FridayBulletin]:
        stmt = select(FridayBulletin).order_by(FridayBulletin.published_date.desc()).offset(skip).limit(limit)
        return list((await self.db.execute(stmt)).scalars().all())

    async def list_content_by_type(self, ctype: str) -> List[CommunityContent]:
        from sqlalchemy import func
        stmt = select(CommunityContent).where(
            func.upper(CommunityContent.content_type) == func.upper(ctype),
            CommunityContent.is_published.is_(True),
        )
        return list((await self.db.execute(stmt)).scalars().all())

    async def list_duas(self, category_id: Optional[int] = None) -> List[Dua]:
        stmt = select(Dua).where(Dua.published.is_(True))
        if category_id:
            stmt = stmt.where(Dua.category_id == category_id)
        return list((await self.db.execute(stmt.order_by(Dua.display_order))).scalars().all())

    async def list_events(self, upcoming_only: bool = False) -> List[Event]:
        stmt = select(Event).where(Event.published.is_(True))
        if upcoming_only:
            stmt = stmt.where(Event.event_date >= date.today())
        return list((await self.db.execute(stmt.order_by(Event.event_date.asc()))).scalars().all())

    async def get_latest_khutba(self) -> Optional[JumaKhutba]:
        stmt = select(JumaKhutba).where(JumaKhutba.published.is_(True)).order_by(JumaKhutba.khutba_date.desc())
        return (await self.db.execute(stmt)).scalars().first()

    async def get_latest_nisab(self) -> Optional[NisabRate]:
        stmt = select(NisabRate).order_by(NisabRate.updated_at.desc())
        return (await self.db.execute(stmt)).scalars().first()

