import uuid, re
from typing import Optional, List
from datetime import datetime, timezone
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from app.models.donations import Donation, SavedDonation
from app.models.transactions import Transaction
from app.models.ratings import Rating
from app.models.categories import Category
from app.repositories.donation_repo import DonationRepository
from app.schemas.v1.donations import DonationCreate, DonationUpdate, DonationResponse

def slugify(text: str) -> str:
    text = re.sub(r"[^\w\s-]", "", text.lower())
    return re.sub(r"[-\s]+", "-", text).strip("-")

class DonationService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.repo = DonationRepository(db)

    async def create_donation(self, data: DonationCreate, user_id: uuid.UUID) -> Donation:
        base_slug = slugify(data.title)
        slug = base_slug
        count = 1
        while await self.repo.get_by_slug(slug):
            slug = f"{base_slug}-{count}"
            count += 1
        now_utc = datetime.now(timezone.utc)
        start_tz = data.start_date if data.start_date.tzinfo else data.start_date.replace(tzinfo=timezone.utc)
        end_tz = data.end_date if data.end_date.tzinfo else data.end_date.replace(tzinfo=timezone.utc)
        donation = Donation(
            **data.model_dump(),
            slug=slug,
            created_by_id=user_id,
            status="Active" if start_tz <= now_utc <= end_tz else "Upcoming"
        )
        created = await self.repo.create(donation)
        await self.db.commit()
        return created

    async def enrich_donation(self, d: Donation) -> DonationResponse:
        tx_stats = await self.db.execute(
            select(func.coalesce(func.sum(Transaction.amount), 0.0), func.count(func.distinct(Transaction.account_number)))
            .where(Transaction.donation_id == d.id, Transaction.payment_status == "Completed")
        )
        row = tx_stats.first()
        collected, donors = float(row[0] or 0.0), int(row[1] or 0)
        avg_rating = (await self.db.execute(select(func.avg(Rating.rating)).where(Rating.donation_id == d.id))).scalar_one_or_none()
        cat = await self.db.get(Category, d.category_id)
        
        now_naive = datetime.now(timezone.utc).replace(tzinfo=None)
        end_naive = d.end_date.replace(tzinfo=None) if d.end_date and d.end_date.tzinfo else d.end_date
        days_left = max(0, (end_naive - now_naive).days) if end_naive else 0
        is_expired = end_naive < now_naive if end_naive else False

        resp = DonationResponse.model_validate(d)
        resp.collected_amount = collected
        resp.donor_count = donors
        resp.average_rating = round(float(avg_rating), 1) if avg_rating else 0.0
        resp.remaining_days = days_left
        resp.is_expired = is_expired
        resp.category_name = cat.category_name if cat else None
        return resp
