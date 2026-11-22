import math, uuid
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from app.api.deps import get_db, get_pagination
from app.repositories.donation_repo import DonationRepository
from app.services.donation_service import DonationService
from app.schemas.common import PaginationParams
from app.schemas.v2.common import PaginatedAPIResponse, PaginationMeta, APIResponse
from app.schemas.v2.donations import DonationV2Response, DonationV2Category

router = APIRouter()

@router.get("", response_model=PaginatedAPIResponse[DonationV2Response])
@router.get("/", response_model=PaginatedAPIResponse[DonationV2Response])
async def list_donations_v2(
    category_id: Optional[uuid.UUID] = None, status: Optional[str] = None, q: Optional[str] = None,
    pagination: PaginationParams = Depends(get_pagination), db: AsyncSession = Depends(get_db)
):
    repo = DonationRepository(db)
    items, total = await repo.search(skip=pagination.skip, limit=pagination.limit, q=q, category_id=category_id, status=status)
    service = DonationService(db)
    v2_items = []
    for d in items:
        enr = await service.enrich_donation(d)
        pct = round((enr.collected_amount / d.target_amount) * 100, 2) if d.target_amount > 0 else 0.0
        v2_items.append(DonationV2Response(
            id=d.id, slug=d.slug, title=d.title, description=d.description,
            target_amount=d.target_amount, collected_amount=enr.collected_amount,
            progress_percentage=pct, donor_count=enr.donor_count, status=d.status,
            is_featured=d.is_featured, is_expired=enr.is_expired, remaining_days=enr.remaining_days,
            category=DonationV2Category(id=d.category_id, name=enr.category_name) if d.category_id else None,
            image_urls=d.image_urls or [], created_at=d.created_at, updated_at=d.updated_at
        ))
    pages = math.ceil(total / pagination.page_size) if total > 0 else 1
    meta = PaginationMeta(page=pagination.page, page_size=pagination.page_size, total_items=total, total_pages=pages, has_next=pagination.page < pages, has_prev=pagination.page > 1)
    return PaginatedAPIResponse(items=v2_items, pagination=meta)

@router.get("/{id_or_slug}", response_model=APIResponse[DonationV2Response])
async def get_donation_v2(id_or_slug: str, db: AsyncSession = Depends(get_db)):
    d = await DonationRepository(db).get_by_id_or_slug(id_or_slug)
    if not d:
        raise HTTPException(status_code=404, detail="Campaign not found")
    enr = await DonationService(db).enrich_donation(d)
    pct = round((enr.collected_amount / d.target_amount) * 100, 2) if d.target_amount > 0 else 0.0
    data = DonationV2Response(
        id=d.id, slug=d.slug, title=d.title, description=d.description,
        target_amount=d.target_amount, collected_amount=enr.collected_amount,
        progress_percentage=pct, donor_count=enr.donor_count, status=d.status,
        is_featured=d.is_featured, is_expired=enr.is_expired, remaining_days=enr.remaining_days,
        category=DonationV2Category(id=d.category_id, name=enr.category_name) if d.category_id else None,
        image_urls=d.image_urls or [], created_at=d.created_at, updated_at=d.updated_at
    )
    return APIResponse(data=data)
