from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import List
import uuid

from app.db.session import get_db
from app.models.transactions import Transaction
from app.schemas.transactions import TransactionResponse, TransactionCreate

router = APIRouter()

@router.get("/", response_model=List[TransactionResponse])
async def read_transactions(skip: int = 0, limit: int = 100, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Transaction).offset(skip).limit(limit))
    return result.scalars().all()

@router.post("/", response_model=TransactionResponse)
async def create_transaction(transaction_in: TransactionCreate, db: AsyncSession = Depends(get_db)):
    db_transaction = Transaction(**transaction_in.model_dump())
    db.add(db_transaction)
    await db.commit()
    await db.refresh(db_transaction)
    return db_transaction

@router.get("/{transaction_id}", response_model=TransactionResponse)
async def read_transaction(transaction_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Transaction).filter(Transaction.id == transaction_id))
    transaction = result.scalars().first()
    if not transaction:
        raise HTTPException(status_code=404, detail="Transaction not found")
    return transaction
