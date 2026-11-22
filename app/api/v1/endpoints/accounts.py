import uuid
from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from app.api.deps import get_db, require_permission
from app.repositories.account_repo import BankAccountRepository
from app.models.transactions import BankAccount
from app.schemas.v1.accounts import BankAccountResponse, BankAccountCreate, BankAccountUpdate

router = APIRouter()

@router.get("/", response_model=List[BankAccountResponse])
async def list_bank_accounts(current_user=Depends(require_permission("accounts.view")), db: AsyncSession = Depends(get_db)):
    return await BankAccountRepository(db).list_active()

@router.post("/", response_model=BankAccountResponse, status_code=status.HTTP_201_CREATED)
async def create_bank_account(data: BankAccountCreate, current_user=Depends(require_permission("accounts.manage")), db: AsyncSession = Depends(get_db)):
    repo = BankAccountRepository(db)
    acc = BankAccount(**data.model_dump())
    created = await repo.create(acc)
    await db.commit()
    return created

@router.get("/{id}", response_model=BankAccountResponse)
async def get_bank_account(id: uuid.UUID, current_user=Depends(require_permission("accounts.view")), db: AsyncSession = Depends(get_db)):
    acc = await BankAccountRepository(db).get_by_id(id)
    if not acc:
        raise HTTPException(status_code=404, detail="Bank account not found")
    return acc

@router.put("/{id}", response_model=BankAccountResponse)
async def update_bank_account(id: uuid.UUID, data: BankAccountUpdate, current_user=Depends(require_permission("accounts.manage")), db: AsyncSession = Depends(get_db)):
    acc = await BankAccountRepository(db).get_by_id(id)
    if not acc:
        raise HTTPException(status_code=404, detail="Bank account not found")
    for f, v in data.model_dump(exclude_unset=True).items():
        setattr(acc, f, v)
    await db.commit()
    return acc

@router.delete("/{id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_bank_account(id: uuid.UUID, current_user=Depends(require_permission("accounts.manage")), db: AsyncSession = Depends(get_db)):
    repo = BankAccountRepository(db)
    acc = await repo.get_by_id(id)
    if not acc:
        raise HTTPException(status_code=404, detail="Bank account not found")
    await repo.delete(acc)
    await db.commit()

