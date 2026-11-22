import math, uuid
from typing import Optional
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from app.api.deps import get_db, get_pagination, require_permission, get_optional_current_user
from app.repositories.transaction_repo import TransactionRepository
from app.services.transaction_service import TransactionService
from app.models.donations import Donation
from app.schemas.common import PaginationParams
from app.schemas.v2.common import PaginatedAPIResponse, PaginationMeta, APIResponse
from app.schemas.v2.transactions import TransactionV2Response, V2PaymentInitiateRequest

router = APIRouter()

@router.get("", response_model=PaginatedAPIResponse[TransactionV2Response])
@router.get("/", response_model=PaginatedAPIResponse[TransactionV2Response])
async def list_transactions_v2(
    donation_id: Optional[uuid.UUID] = None, status: Optional[str] = None,
    payment_method: Optional[str] = None, search: Optional[str] = None,
    pagination: PaginationParams = Depends(get_pagination),
    current_user=Depends(require_permission("donations.view")),
    db: AsyncSession = Depends(get_db)
):
    repo = TransactionRepository(db)
    items, total = await repo.search(skip=pagination.skip, limit=pagination.limit, donation_id=donation_id, status=status, payment_method=payment_method, search_query=search)
    v2_items = []
    for t in items:
        d = await db.get(Donation, t.donation_id) if t.donation_id else None
        v2_items.append(TransactionV2Response(
            id=t.id, donation_id=t.donation_id, donation_title=d.title if d else None,
            amount=t.amount, currency="KES", payment_method=t.payment_method,
            payment_status=t.payment_status, transaction_reference=t.transaction_reference,
            mpesa_receipt=t.mpesa_receipt, donor_name=t.account_name,
            donated_at=t.donated_at, completed_at=t.completed_at
        ))
    pages = math.ceil(total / pagination.page_size) if total > 0 else 1
    meta = PaginationMeta(page=pagination.page, page_size=pagination.page_size, total_items=total, total_pages=pages, has_next=pagination.page < pages, has_prev=pagination.page > 1)
    return PaginatedAPIResponse(items=v2_items, pagination=meta)

@router.post("/pay", response_model=APIResponse[dict])
async def initiate_payment_v2(
    req: V2PaymentInitiateRequest, current_user=Depends(get_optional_current_user), db: AsyncSession = Depends(get_db)
):
    uid = current_user.id if current_user else None
    res = await TransactionService(db).initiate_stk(donation_id=req.donation_id, phone_number=req.phone_number, amount=req.amount, user_id=uid)
    return APIResponse(data=res, message="STK push prompt sent to donor device")
