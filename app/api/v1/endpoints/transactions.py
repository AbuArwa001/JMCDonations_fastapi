import uuid
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from app.api.deps import get_db, require_permission
from app.repositories.transaction_repo import TransactionRepository
from app.services.transaction_service import TransactionService
from app.schemas.v1.transactions import (
    TransactionResponse, TransactionUpdate, BulkDeleteTransactionsRequest,
    BulkDeleteTransactionsResponse
)
from app.models.transactions import Transaction

router = APIRouter()

@router.get("/", response_model=List[TransactionResponse])
async def list_transactions(
    skip: int = Query(0, ge=0), limit: int = Query(50, ge=1, le=100),
    donation_id: Optional[uuid.UUID] = None, status: Optional[str] = None,
    payment_method: Optional[str] = None, search: Optional[str] = None,
    current_user=Depends(require_permission("donations.view")), db: AsyncSession = Depends(get_db)
):
    repo = TransactionRepository(db)
    items, _ = await repo.search(skip=skip, limit=limit, donation_id=donation_id, status=status, payment_method=payment_method, search_query=search)
    return items

@router.get("/{id}", response_model=TransactionResponse)
async def get_transaction(id: uuid.UUID, current_user=Depends(require_permission("donations.view")), db: AsyncSession = Depends(get_db)):
    tx = await TransactionRepository(db).get_by_id(id)
    if not tx:
        raise HTTPException(status_code=404, detail="Transaction not found")
    return tx

@router.put("/{id}", response_model=TransactionResponse)
async def update_transaction(id: uuid.UUID, data: TransactionUpdate, current_user=Depends(require_permission("donations.manage")), db: AsyncSession = Depends(get_db)):
    tx = await TransactionRepository(db).get_by_id(id)
    if not tx:
        raise HTTPException(status_code=404, detail="Transaction not found")
    for field, val in data.model_dump(exclude_unset=True).items():
        setattr(tx, field, val)
    await db.commit()
    return tx

@router.post("/verify-cash/{id}", response_model=TransactionResponse)
async def verify_cash_transaction(id: uuid.UUID, current_user=Depends(require_permission("donations.manage")), db: AsyncSession = Depends(get_db)):
    return await TransactionService(db).verify_cash(id, current_user.id)

@router.delete("/{id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_transaction(id: uuid.UUID, current_user=Depends(require_permission("donations.delete")), db: AsyncSession = Depends(get_db)):
    repo = TransactionRepository(db)
    tx = await repo.get_by_id(id)
    if not tx:
        raise HTTPException(status_code=404, detail="Transaction not found")
    await repo.delete(tx)
    await db.commit()

@router.post("/bulk-delete", response_model=BulkDeleteTransactionsResponse)
async def bulk_delete_transactions(req: BulkDeleteTransactionsRequest, current_user=Depends(require_permission("donations.delete")), db: AsyncSession = Depends(get_db)):
    count = await TransactionRepository(db).bulk_delete(req.transaction_ids)
    await db.commit()
    return BulkDeleteTransactionsResponse(deleted_count=count, message=f"Successfully deleted {count} transactions")

