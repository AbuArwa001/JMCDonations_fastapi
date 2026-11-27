import uuid
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from app.api.deps import get_db, require_permission, get_optional_current_user, get_current_user
from app.repositories.transaction_repo import TransactionRepository
from app.services.transaction_service import TransactionService
from app.services.stk_service import stk_service
from app.services.card_payment_service import card_payment_service
from app.services.paypal_payment_service import paypal_payment_service
from app.schemas.v1.transactions import (
    TransactionResponse, TransactionUpdate, BulkDeleteTransactionsRequest,
    BulkDeleteTransactionsResponse, STKPushInput, PayPalInitInput,
    CardPaymentInput, FlutterwaveVerifyInput
)
router = APIRouter()
# ── Mobile Payment Endpoints ───────────────────────────────────────────────
@router.post("/initiate_stk_push")
@router.post("/initiate_stk_push/", include_in_schema=False)
@router.post("/initiate-stk-push", include_in_schema=False)
@router.post("/initiate-stk-push/", include_in_schema=False)
async def initiate_stk_push(payload: STKPushInput, user=Depends(get_optional_current_user), db: AsyncSession = Depends(get_db)):
    return await stk_service.initiate_stk_push(db, payload, user)
@router.get("/check_status")
@router.get("/check_status/", include_in_schema=False)
@router.get("/check-status", include_in_schema=False)
@router.get("/check-status/", include_in_schema=False)
async def check_status(reference: str, db: AsyncSession = Depends(get_db)):
    return await stk_service.check_status(db, reference)
@router.post("/initiate_card_payment", status_code=status.HTTP_201_CREATED)
@router.post("/initiate_card_payment/", status_code=status.HTTP_201_CREATED, include_in_schema=False)
@router.post("/initiate-card-payment", status_code=status.HTTP_201_CREATED, include_in_schema=False)
@router.post("/initiate-card-payment/", status_code=status.HTTP_201_CREATED, include_in_schema=False)
async def initiate_card_payment(payload: CardPaymentInput, user=Depends(get_optional_current_user), db: AsyncSession = Depends(get_db)):
    return await card_payment_service.initiate_card(db, payload, user)
@router.post("/verify_flutterwave_payment")
@router.post("/verify_flutterwave_payment/", include_in_schema=False)
@router.post("/verify-flutterwave-payment", include_in_schema=False)
@router.post("/verify-flutterwave-payment/", include_in_schema=False)
async def verify_flutterwave_payment(payload: FlutterwaveVerifyInput, user=Depends(get_optional_current_user), db: AsyncSession = Depends(get_db)):
    return await card_payment_service.verify_flutterwave(db, payload, user)
@router.post("/initiate_paypal_payment")
@router.post("/initiate_paypal_payment/", include_in_schema=False)
@router.post("/initiate-paypal-payment", include_in_schema=False)
@router.post("/initiate-paypal-payment/", include_in_schema=False)
async def initiate_paypal_payment(payload: PayPalInitInput, user=Depends(get_optional_current_user), db: AsyncSession = Depends(get_db)):
    return await paypal_payment_service.initiate_paypal(db, payload, user)
@router.get("/paypal_callback")
@router.get("/paypal_callback/", include_in_schema=False)
@router.get("/paypal-callback", include_in_schema=False)
@router.get("/paypal-callback/", include_in_schema=False)
async def paypal_callback(tx_id: Optional[str] = None, token: Optional[str] = None, cancel: Optional[str] = None, db: AsyncSession = Depends(get_db)):
    return await paypal_payment_service.handle_callback(db, tx_id, token, cancel)
# ── Standard CRUD & Admin Endpoints ────────────────────────────────────────
@router.get("/me", response_model=List[TransactionResponse])
@router.get("/me/", response_model=List[TransactionResponse])
@router.get("/my-donations", response_model=List[TransactionResponse])
@router.get("/my-donations/", response_model=List[TransactionResponse])
async def list_my_transactions(
    skip: int = Query(0, ge=0), limit: int = Query(50, ge=1, le=100),
    status: Optional[str] = None, payment_method: Optional[str] = None,
    user=Depends(get_current_user), db: AsyncSession = Depends(get_db)
):
    items, _ = await TransactionRepository(db).search(
        skip=skip, limit=limit, status=status, payment_method=payment_method,
        user_id=user.id, phone_number=user.phone_number
    )
    return items

@router.get("/", response_model=List[TransactionResponse])
@router.get("", response_model=List[TransactionResponse], include_in_schema=False)
async def list_transactions(
    skip: int = Query(0, ge=0), limit: int = Query(50, ge=1, le=100), donation_id: Optional[uuid.UUID] = None,
    status: Optional[str] = None, payment_method: Optional[str] = None, search: Optional[str] = None,
    mine: Optional[bool] = Query(None),
    user=Depends(get_current_user), db: AsyncSession = Depends(get_db)
):
    if mine or not (user.is_admin or getattr(user, "is_superuser", False)):
        uid = user.id
        phone = user.phone_number
    else:
        uid = None
        phone = None
    items, _ = await TransactionRepository(db).search(
        skip=skip, limit=limit, donation_id=donation_id, status=status,
        payment_method=payment_method, search_query=search, user_id=uid, phone_number=phone
    )
    return items
@router.post("/verify-cash/{id}", response_model=TransactionResponse)
async def verify_cash_transaction(id: uuid.UUID, user=Depends(require_permission("donations.manage")), db: AsyncSession = Depends(get_db)):
    return await TransactionService(db).verify_cash(id, user.id)
@router.post("/bulk-delete", response_model=BulkDeleteTransactionsResponse)
@router.post("/bulk-delete/", response_model=BulkDeleteTransactionsResponse, include_in_schema=False)
async def bulk_delete_transactions(req: BulkDeleteTransactionsRequest, user=Depends(require_permission("donations.delete")), db: AsyncSession = Depends(get_db)):
    count = await TransactionRepository(db).bulk_delete(req.transaction_ids)
    await db.commit()
    return BulkDeleteTransactionsResponse(deleted_count=count, message=f"Successfully deleted {count} transactions")
@router.get("/{id}", response_model=TransactionResponse)
async def get_transaction(id: uuid.UUID, user=Depends(require_permission("donations.view")), db: AsyncSession = Depends(get_db)):
    tx = await TransactionRepository(db).get_by_id(id)
    if not tx: raise HTTPException(status_code=404, detail="Transaction not found")
    return tx
@router.put("/{id}", response_model=TransactionResponse)
async def update_transaction(id: uuid.UUID, data: TransactionUpdate, user=Depends(require_permission("donations.manage")), db: AsyncSession = Depends(get_db)):
    tx = await TransactionRepository(db).get_by_id(id)
    if not tx: raise HTTPException(status_code=404, detail="Transaction not found")
    for field, val in data.model_dump(exclude_unset=True).items(): setattr(tx, field, val)
    await db.commit(); return tx
@router.delete("/{id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_transaction(id: uuid.UUID, user=Depends(require_permission("donations.delete")), db: AsyncSession = Depends(get_db)):
    repo = TransactionRepository(db)
    tx = await repo.get_by_id(id)
    if not tx: raise HTTPException(status_code=404, detail="Transaction not found")
    await repo.delete(tx); await db.commit()
