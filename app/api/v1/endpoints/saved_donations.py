import uuid
from typing import List, Optional
from pydantic import BaseModel
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from app.api.deps import get_db, get_current_user
from app.repositories.donation_repo import DonationRepository
from app.services.donation_service import DonationService
from app.models.donations import SavedDonation
from app.models.users import User
from app.schemas.v1.donations import SavedDonationResponse

router = APIRouter()

class SaveDonationBody(BaseModel):
    donation_id: Optional[str] = None

@router.get("/saved", response_model=List[SavedDonationResponse])
@router.get("/saved/", response_model=List[SavedDonationResponse])
async def list_saved_donations(current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    saved_items = await DonationRepository(db).list_saved(current_user.id)
    service = DonationService(db)
    result = []
    for s in saved_items:
        if s.donation and not s.donation.is_deleted:
            enriched = await service.enrich_donation(s.donation)
            result.append(SavedDonationResponse(id=s.id, user_id=s.user_id, donation_id=s.donation_id, donation=enriched, saved_at=s.saved_at))
    return result

@router.get("/saved_ids", response_model=List[str])
@router.get("/saved_ids/", response_model=List[str])
@router.get("/saved-ids", response_model=List[str])
@router.get("/saved-ids/", response_model=List[str])
async def list_saved_donation_ids(current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    saved_items = await DonationRepository(db).list_saved(current_user.id)
    return [str(s.donation_id) for s in saved_items if s.donation and not s.donation.is_deleted]

@router.post("/save", response_model=SavedDonationResponse)
@router.post("/save/", response_model=SavedDonationResponse)
async def save_donation_by_body(body: SaveDonationBody, current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    if not body.donation_id:
        raise HTTPException(status_code=400, detail="donation_id is required")
    return await save_donation_by_id(body.donation_id, current_user, db)

@router.post("/{id_or_slug}/save", response_model=SavedDonationResponse)
@router.post("/{id_or_slug}/save/", response_model=SavedDonationResponse)
@router.post("/{id_or_slug}/saved", response_model=SavedDonationResponse)
@router.post("/{id_or_slug}/saved/", response_model=SavedDonationResponse)
async def save_donation_by_id(id_or_slug: str, current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    repo = DonationRepository(db)
    d = await repo.get_by_id_or_slug(id_or_slug)
    if not d:
        raise HTTPException(status_code=404, detail="Donation campaign not found")
    saved = await repo.get_saved(current_user.id, d.id)
    if not saved:
        saved = SavedDonation(user_id=current_user.id, donation_id=d.id)
        db.add(saved)
        await db.commit()
        await db.refresh(saved)
    enriched = await DonationService(db).enrich_donation(d)
    return SavedDonationResponse(id=saved.id, user_id=saved.user_id, donation_id=saved.donation_id, donation=enriched, saved_at=saved.saved_at)

@router.delete("/{id_or_slug}/unsave", status_code=status.HTTP_204_NO_CONTENT)
@router.delete("/{id_or_slug}/unsave/", status_code=status.HTTP_204_NO_CONTENT)
@router.delete("/{id_or_slug}/save", status_code=status.HTTP_204_NO_CONTENT)
@router.delete("/{id_or_slug}/saved", status_code=status.HTTP_204_NO_CONTENT)
async def unsave_donation_by_id(id_or_slug: str, current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    repo = DonationRepository(db)
    d = await repo.get_by_id_or_slug(id_or_slug)
    if not d:
        raise HTTPException(status_code=404, detail="Donation campaign not found")
    saved = await repo.get_saved(current_user.id, d.id)
    if saved:
        await db.delete(saved)
        await db.commit()
    return None
