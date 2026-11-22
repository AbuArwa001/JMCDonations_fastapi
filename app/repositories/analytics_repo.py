from typing import Dict, Any, List
from datetime import datetime, timedelta, timezone
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from app.models.transactions import Transaction
from app.models.donations import Donation
from app.models.categories import Category

class AnalyticsRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_overview_totals(self) -> Dict[str, float]:
        now = datetime.now(timezone.utc)
        week_ago = now - timedelta(days=7)
        month_ago = now - timedelta(days=30)

        total_stmt = select(func.coalesce(func.sum(Transaction.amount), 0.0)).where(Transaction.payment_status == "Completed")
        week_stmt = total_stmt.where(Transaction.donated_at >= week_ago)
        month_stmt = total_stmt.where(Transaction.donated_at >= month_ago)

        total = (await self.db.execute(total_stmt)).scalar_one()
        week = (await self.db.execute(week_stmt)).scalar_one()
        month = (await self.db.execute(month_stmt)).scalar_one()

        return {
            "total_collected": float(total),
            "total_collected_week": float(week),
            "total_collected_month": float(month),
        }

    async def get_category_breakdown(self) -> List[Dict[str, Any]]:
        stmt = (
            select(Category.category_name, Category.color, func.coalesce(func.sum(Transaction.amount), 0.0))
            .join(Donation, Donation.category_id == Category.id)
            .join(Transaction, Transaction.donation_id == Donation.id)
            .where(Transaction.payment_status == "Completed")
            .group_by(Category.id, Category.category_name, Category.color)
        )
        result = await self.db.execute(stmt)
        return [{"category_name": r[0], "color": r[1], "total_amount": float(r[2])} for r in result.all()]

