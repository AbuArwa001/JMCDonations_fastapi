import uuid
from typing import Optional, List, Tuple
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, or_
from app.repositories.base import BaseRepository
from app.models.donations import Donation, SavedDonation

class DonationRepository(BaseRepository[Donation]):
    def __init__(self, db: AsyncSession):
        super().__init__(Donation, db)

    async def get_by_slug(self, slug: str) -> Optional[Donation]:
        stmt = select(Donation).where(Donation.slug == slug, Donation.is_deleted.is_(False))
        result = await self.db.execute(stmt)
        return result.scalars().first()

    async def get_by_id_or_slug(self, id_or_slug: str) -> Optional[Donation]:
        try:
            uid = uuid.UUID(id_or_slug)
            stmt = select(Donation).where(Donation.id == uid, Donation.is_deleted.is_(False))
        except ValueError:
            stmt = select(Donation).where(Donation.slug == id_or_slug, Donation.is_deleted.is_(False))
        result = await self.db.execute(stmt)
        return result.scalars().first()

    async def search(
        self, skip: int = 0, limit: int = 20, q: Optional[str] = None,
        category_id: Optional[uuid.UUID] = None, status: Optional[str] = None,
        is_featured: Optional[bool] = None
    ) -> Tuple[List[Donation], int]:
        stmt = select(Donation).where(Donation.is_deleted.is_(False))
        count_stmt = select(func.count(Donation.id)).where(Donation.is_deleted.is_(False))
        if q:
            cond = or_(Donation.title.ilike(f"%{q}%"), Donation.description.ilike(f"%{q}%"))
            stmt, count_stmt = stmt.where(cond), count_stmt.where(cond)
        if category_id:
            stmt, count_stmt = stmt.where(Donation.category_id == category_id), count_stmt.where(Donation.category_id == category_id)
        if status:
            stmt, count_stmt = stmt.where(Donation.status == status), count_stmt.where(Donation.status == status)
        if is_featured is not None:
            stmt, count_stmt = stmt.where(Donation.is_featured == is_featured), count_stmt.where(Donation.is_featured == is_featured)
        total = (await self.db.execute(count_stmt)).scalar_one() or 0
        result = await self.db.execute(stmt.order_by(Donation.created_at.desc()).offset(skip).limit(limit))
        return list(result.scalars().all()), total

    async def get_saved(self, user_id: uuid.UUID, donation_id: uuid.UUID) -> Optional[SavedDonation]:
        stmt = select(SavedDonation).where(SavedDonation.user_id == user_id, SavedDonation.donation_id == donation_id)
        return (await self.db.execute(stmt)).scalars().first()

    async def list_saved(self, user_id: uuid.UUID) -> List[SavedDonation]:
        from sqlalchemy.orm import selectinload
        stmt = (
            select(SavedDonation)
            .options(selectinload(SavedDonation.donation))
            .where(SavedDonation.user_id == user_id)
            .order_by(SavedDonation.saved_at.desc())
        )
        return list((await self.db.execute(stmt)).scalars().all())

