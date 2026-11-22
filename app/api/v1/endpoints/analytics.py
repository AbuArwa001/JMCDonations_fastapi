from typing import List, Dict, Any
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from app.api.deps import get_db, require_permission
from app.services.analytics_service import AnalyticsService
from app.schemas.v1.analytics import DashboardSummaryResponse, CategoryBreakdownResponse

router = APIRouter()

@router.get("/overview", response_model=DashboardSummaryResponse)
async def get_overview_analytics(current_user=Depends(require_permission("dashboard.view")), db: AsyncSession = Depends(get_db)):
    return await AnalyticsService(db).get_dashboard_summary()

@router.get("/categories", response_model=List[CategoryBreakdownResponse])
async def get_category_analytics(current_user=Depends(require_permission("dashboard.view")), db: AsyncSession = Depends(get_db)):
    breakdown = await AnalyticsService(db).get_category_breakdown()
    return [CategoryBreakdownResponse(**b) for b in breakdown]

