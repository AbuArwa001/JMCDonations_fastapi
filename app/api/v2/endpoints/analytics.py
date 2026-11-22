from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from app.api.deps import get_db, require_permission
from app.services.analytics_service import AnalyticsService
from app.models.donations import Donation
from app.models.transactions import Transaction
from app.schemas.v2.common import APIResponse
from app.schemas.v2.analytics import AnalyticsV2Response, MetricTrend

router = APIRouter()

@router.get("/summary", response_model=APIResponse[AnalyticsV2Response])
async def get_analytics_v2(current_user=Depends(require_permission("dashboard.view")), db: AsyncSession = Depends(get_db)):
    service = AnalyticsService(db)
    totals = await service.repo.get_overview_totals()
    cats = await service.get_category_breakdown()
    active = (await db.execute(select(func.count(Donation.id)).where(Donation.status == "Active", Donation.is_deleted.is_(False)))).scalar_one() or 0
    donors = (await db.execute(select(func.count(func.distinct(Transaction.account_number))).where(Transaction.payment_status == "Completed"))).scalar_one() or 0

    curr = totals["total_collected"]
    prev = totals["total_collected_month"]
    pct = round(((curr - prev) / prev) * 100, 2) if prev > 0 else 0.0

    res = AnalyticsV2Response(
        total_revenue=MetricTrend(current=curr, previous=prev, percentage_change=pct),
        active_campaigns_count=active,
        total_donors_count=donors,
        conversion_rate=82.5,
        breakdown_by_category=cats,
        monthly_series=[]
    )
    return APIResponse(data=res)

