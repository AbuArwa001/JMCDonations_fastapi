from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from app.api.deps import get_db, require_permission
from app.services.community_service import CommunityService
from app.repositories.community_repo import CommunityRepository
from app.schemas.v1.zakat import NisabRateResponse, NisabRateUpdate, NisabRateCreate

router = APIRouter()

@router.get("/nisab", response_model=NisabRateResponse)
@router.get("/nisab/", response_model=NisabRateResponse)
@router.get("/nisab-rate", response_model=NisabRateResponse)
@router.get("/nisab-rate/", response_model=NisabRateResponse)
async def get_nisab(db: AsyncSession = Depends(get_db)):
    rate = await CommunityRepository(db).get_latest_nisab()
    if not rate:
        raise HTTPException(status_code=404, detail="Nisab rate not set")
    return rate

@router.put("/nisab", response_model=NisabRateResponse)
@router.put("/nisab/", response_model=NisabRateResponse)
@router.post("/nisab", response_model=NisabRateResponse)
@router.post("/nisab/", response_model=NisabRateResponse)
@router.patch("/nisab", response_model=NisabRateResponse)
@router.patch("/nisab/", response_model=NisabRateResponse)
@router.put("/nisab-rate", response_model=NisabRateResponse)
@router.put("/nisab-rate/", response_model=NisabRateResponse)
@router.patch("/nisab-rate", response_model=NisabRateResponse)
@router.patch("/nisab-rate/", response_model=NisabRateResponse)
@router.post("/nisab-rate", response_model=NisabRateResponse)
@router.post("/nisab-rate/", response_model=NisabRateResponse)
async def update_nisab(data: NisabRateCreate, current_user=Depends(require_permission("zakat.manage")), db: AsyncSession = Depends(get_db)):
    return await CommunityService(db).update_nisab_rates(data.gold_price_per_gram, data.silver_price_per_gram, current_user.id)

