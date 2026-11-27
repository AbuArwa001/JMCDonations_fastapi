import uuid
from typing import List, Optional
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from app.api.deps import get_db, get_current_user, require_permission
from app.repositories.donation_repo import DonationRepository
from app.services.donation_service import DonationService
from app.models.donations import Donation, SavedDonation
from app.models.users import User
from app.schemas.v1.donations import DonationResponse, DonationCreate, DonationUpdate, SavedDonationResponse

router = APIRouter()

@router.get("", response_model=List[DonationResponse])
@router.get("/", response_model=List[DonationResponse])
async def list_donations(
    skip: int = Query(0, ge=0), limit: int = Query(20, ge=1, le=100),
    category_id: Optional[uuid.UUID] = None, status: Optional[str] = None,
    q: Optional[str] = None, db: AsyncSession = Depends(get_db)
):
    repo = DonationRepository(db)
    items, _ = await repo.search(skip=skip, limit=limit, q=q, category_id=category_id, status=status)
    service = DonationService(db)
    return [await service.enrich_donation(d) for d in items]

@router.get("/active", response_model=List[DonationResponse])
async def list_active_donations(db: AsyncSession = Depends(get_db)):
    repo = DonationRepository(db)
    items, _ = await repo.search(status="Active", limit=50)
    service = DonationService(db)
    return [await service.enrich_donation(d) for d in items]

@router.get("/featured", response_model=List[DonationResponse])
async def list_featured_donations(db: AsyncSession = Depends(get_db)):
    repo = DonationRepository(db)
    items, _ = await repo.search(is_featured=True, limit=20)
    service = DonationService(db)
    return [await service.enrich_donation(d) for d in items]

@router.post("", response_model=DonationResponse, status_code=status.HTTP_201_CREATED)
@router.post("/", response_model=DonationResponse, status_code=status.HTTP_201_CREATED)
async def create_donation(
    data: DonationCreate, current_user: User = Depends(require_permission("drives.manage")),
    db: AsyncSession = Depends(get_db)
):
    service = DonationService(db)
    d = await service.create_donation(data, current_user.id)
    return await service.enrich_donation(d)

@router.get("/{id_or_slug}", response_model=DonationResponse)
async def get_donation(id_or_slug: str, db: AsyncSession = Depends(get_db)):
    d = await DonationRepository(db).get_by_id_or_slug(id_or_slug)
    if not d:
        raise HTTPException(status_code=404, detail="Donation campaign not found")
    return await DonationService(db).enrich_donation(d)

@router.put("/{id_or_slug}", response_model=DonationResponse)
async def update_donation(
    id_or_slug: str, data: DonationUpdate,
    current_user: User = Depends(require_permission("drives.manage")),
    db: AsyncSession = Depends(get_db)
):
    d = await DonationRepository(db).get_by_id_or_slug(id_or_slug)
    if not d:
        raise HTTPException(status_code=404, detail="Donation campaign not found")
    for field, val in data.model_dump(exclude_unset=True).items():
        setattr(d, field, val)
    await db.commit()
    return await DonationService(db).enrich_donation(d)

@router.delete("/{id_or_slug}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_donation(
    id_or_slug: str, current_user: User = Depends(require_permission("drives.manage")),
    db: AsyncSession = Depends(get_db)
):
    repo = DonationRepository(db)
    d = await repo.get_by_id_or_slug(id_or_slug)
    if not d:
        raise HTTPException(status_code=404, detail="Donation not found")
    d.is_deleted = True
    d.deleted_at = datetime.now(timezone.utc).replace(tzinfo=None)
    await db.commit()

