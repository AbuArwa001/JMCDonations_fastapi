from typing import Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from app.repositories.analytics_repo import AnalyticsRepository
from app.models.donations import Donation
from app.schemas.v1.analytics import DashboardSummaryResponse

class AnalyticsService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.repo = AnalyticsRepository(db)

    async def get_dashboard_summary(self) -> DashboardSummaryResponse:
        totals = await self.repo.get_overview_totals()
        active_drives = (await self.db.execute(select(func.count(Donation.id)).where(Donation.status == "Active", Donation.is_deleted.is_(False)))).scalar_one() or 0
        return DashboardSummaryResponse(
            total_collected=totals["total_collected"],
            total_collected_week=totals["total_collected_week"],
            total_collected_month=totals["total_collected_month"],
            active_drives=active_drives,
            donation_trends=[]
        )

    async def get_category_breakdown(self):
        return await self.repo.get_category_breakdown()

