import uuid
from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from app.api.deps import get_db, require_permission
from app.repositories.account_repo import TransferRepository
from app.models.transactions import Transfer
from app.schemas.v1.accounts import TransferResponse, TransferCreate

router = APIRouter()

@router.get("/", response_model=List[TransferResponse])
async def list_transfers(current_user=Depends(require_permission("transfers.view")), db: AsyncSession = Depends(get_db)):
    return await TransferRepository(db).list_transfers()

@router.post("/", response_model=TransferResponse, status_code=status.HTTP_201_CREATED)
async def initiate_transfer(data: TransferCreate, current_user=Depends(require_permission("transfers.manage")), db: AsyncSession = Depends(get_db)):
    repo = TransferRepository(db)
    ref = f"TRF-{uuid.uuid4().hex[:8].upper()}"
    transfer = Transfer(
        source_paybill=data.source_paybill or "150770",
        destination_account_id=data.destination_account_id,
        amount=data.amount,
        description=data.description,
        transaction_reference=ref,
        status="Pending"
    )
    created = await repo.create(transfer)
    await db.commit()
    return created

