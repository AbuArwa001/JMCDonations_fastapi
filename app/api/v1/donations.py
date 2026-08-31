from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import List
import uuid

from app.db.session import get_db
from app.models.donations import Donation
from app.schemas.donations import DonationResponse, DonationCreate, DonationUpdate

router = APIRouter()

@router.get("/", response_model=List[DonationResponse])
async def read_donations(skip: int = 0, limit: int = 100, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Donation).offset(skip).limit(limit))
    return result.scalars().all()

@router.post("/", response_model=DonationResponse)
async def create_donation(donation_in: DonationCreate, db: AsyncSession = Depends(get_db)):
    # Note: In reality, created_by_id would come from current_user
    db_donation = Donation(**donation_in.model_dump())
    # Temporary mock of user ID until full auth middleware is in place
    # db_donation.created_by_id = current_user.id
    
    db.add(db_donation)
    await db.commit()
    await db.refresh(db_donation)
    return db_donation

@router.get("/{donation_id}", response_model=DonationResponse)
async def read_donation(donation_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Donation).filter(Donation.id == donation_id))
    donation = result.scalars().first()
    if not donation:
        raise HTTPException(status_code=404, detail="Donation not found")
    return donation
