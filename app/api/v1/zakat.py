import uuid
from datetime import datetime, timezone
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel

from app.db.session import get_db
from app.models.zakat import NisabRate
from app.models.users import User
from app.schemas.zakat import NisabRateCreate, NisabRateUpdate, NisabRateResponse
from app.api.dependencies.auth import get_current_admin_user

router = APIRouter()

class ZakatCalculateRequest(BaseModel):
    cash_in_hand_or_bank: float = 0.0
    gold_grams: float = 0.0
    silver_grams: float = 0.0
    other_investments: float = 0.0
    money_owed_to_you: float = 0.0
    short_term_debts: float = 0.0

class ZakatCalculateResponse(BaseModel):
    nisab_threshold_kes: float
    total_wealth_kes: float
    net_zakat_eligible_kes: float
    is_zakat_due: bool
    zakat_payable_kes: float
    nisab_rate: NisabRateResponse

@router.get("/nisab", response_model=NisabRateResponse)
@router.get("/nisab-rate", response_model=NisabRateResponse)
async def get_nisab_rate(db: AsyncSession = Depends(get_db)):
    """
    Get current active Nisab rate for gold and silver.
    """
    result = await db.execute(select(NisabRate).order_by(NisabRate.updated_at.desc()))
    db_rate = result.scalars().first()
    if not db_rate:
        # Default baseline if table is freshly initialized
        db_rate = NisabRate(
            gold_price_per_gram=9500.0,
            silver_price_per_gram=120.0,
            currency="KES",
            updated_at=datetime.now(timezone.utc).replace(tzinfo=None)
        )
        db.add(db_rate)
        await db.commit()
        await db.refresh(db_rate)
    return db_rate

@router.post("/nisab", response_model=NisabRateResponse, status_code=status.HTTP_201_CREATED)
@router.post("/nisab-rate", response_model=NisabRateResponse, status_code=status.HTTP_201_CREATED)
async def create_nisab_rate(
    rate_in: NisabRateCreate,
    current_user: User = Depends(get_current_admin_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Update or create a new Nisab rate (Admin only).
    """
    db_rate = NisabRate(
        **rate_in.model_dump(),
        updated_by_id=current_user.id,
        updated_at=datetime.now(timezone.utc).replace(tzinfo=None)
    )
    db.add(db_rate)
    await db.commit()
    await db.refresh(db_rate)
    return db_rate

@router.put("/nisab/{rate_id}", response_model=NisabRateResponse)
async def update_nisab_rate(
    rate_id: uuid.UUID,
    rate_in: NisabRateUpdate,
    current_user: User = Depends(get_current_admin_user),
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(select(NisabRate).filter(NisabRate.id == rate_id))
    rate = result.scalars().first()
    if not rate:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Nisab rate not found")

    update_data = rate_in.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(rate, field, value)

    rate.updated_at = datetime.now(timezone.utc).replace(tzinfo=None)
    rate.updated_by_id = current_user.id
    await db.commit()
    await db.refresh(rate)
    return rate

@router.post("/calculate", response_model=ZakatCalculateResponse)
async def calculate_zakat(
    calc_in: ZakatCalculateRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    Calculate Zakat due (2.5%) based on the latest Nisab threshold (silver benchmark: 612.36g, gold: 87.48g).
    """
    rate_res = await db.execute(select(NisabRate).order_by(NisabRate.updated_at.desc()))
    rate = rate_res.scalars().first()
    if not rate:
        rate = NisabRate(
            gold_price_per_gram=9500.0,
            silver_price_per_gram=120.0,
            currency="KES",
            updated_at=datetime.now(timezone.utc).replace(tzinfo=None)
        )
        db.add(rate)
        await db.commit()
        await db.refresh(rate)

    # Silver Nisab is standard for charity/benefit of the poor (612.36g)
    nisab_silver_threshold = float(rate.silver_price_per_gram) * 612.36
    
    # Calculate assets
    gold_val = calc_in.gold_grams * float(rate.gold_price_per_gram)
    silver_val = calc_in.silver_grams * float(rate.silver_price_per_gram)
    total_wealth = (
        calc_in.cash_in_hand_or_bank +
        gold_val +
        silver_val +
        calc_in.other_investments +
        calc_in.money_owed_to_you
    )
    net_eligible = max(0.0, total_wealth - calc_in.short_term_debts)

    is_due = net_eligible >= nisab_silver_threshold
    zakat_due = round(net_eligible * 0.025, 2) if is_due else 0.0

    return ZakatCalculateResponse(
        nisab_threshold_kes=round(nisab_silver_threshold, 2),
        total_wealth_kes=round(total_wealth, 2),
        net_zakat_eligible_kes=round(net_eligible, 2),
        is_zakat_due=is_due,
        zakat_payable_kes=zakat_due,
        nisab_rate=rate
    )
