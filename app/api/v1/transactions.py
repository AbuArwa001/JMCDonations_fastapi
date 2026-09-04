import uuid
from datetime import datetime, timezone
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.db.session import get_db
from app.models.transactions import Transaction, BankAccount, Transfer
from app.models.donations import Donation
from app.models.users import User
from app.schemas.transactions import (
    TransactionCreate, TransactionUpdate, TransactionResponse,
    BankAccountCreate, BankAccountUpdate, BankAccountResponse,
    TransferCreate, TransferResponse
)
from app.api.dependencies.auth import get_current_active_user, get_current_admin_user

router = APIRouter()

# ==================== Transactions ====================

@router.get("/", response_model=List[TransactionResponse])
async def list_transactions(
    skip: int = 0,
    limit: int = 100,
    donation_id: Optional[uuid.UUID] = None,
    user_id: Optional[uuid.UUID] = None,
    payment_status: Optional[str] = None,
    payment_method: Optional[str] = None,
    db: AsyncSession = Depends(get_db)
):
    """
    List transactions with optional filtering.
    """
    query = select(Transaction)
    if donation_id:
        query = query.filter(Transaction.donation_id == donation_id)
    if user_id:
        query = query.filter(Transaction.user_id == user_id)
    if payment_status:
        query = query.filter(Transaction.payment_status == payment_status)
    if payment_method:
        query = query.filter(Transaction.payment_method == payment_method)

    query = query.order_by(Transaction.donated_at.desc()).offset(skip).limit(limit)
    result = await db.execute(query)
    return result.scalars().all()

@router.post("/", response_model=TransactionResponse, status_code=status.HTTP_201_CREATED)
async def create_transaction(
    transaction_in: TransactionCreate,
    db: AsyncSession = Depends(get_db)
):
    """
    Record a new transaction.
    """
    # Verify donation exists
    d_res = await db.execute(select(Donation).filter(Donation.id == transaction_in.donation_id, Donation.is_deleted == False))
    donation = d_res.scalars().first()
    if not donation:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Donation drive not found")

    ref = f"TX-{uuid.uuid4().hex[:10].upper()}"
    db_tx = Transaction(
        **transaction_in.model_dump(),
        transaction_reference=ref,
        payment_status="Pending",
        donated_at=datetime.now(timezone.utc).replace(tzinfo=None)
    )
    db.add(db_tx)
    await db.commit()
    await db.refresh(db_tx)
    return db_tx

@router.get("/{transaction_id}", response_model=TransactionResponse)
async def get_transaction(transaction_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Transaction).filter(Transaction.id == transaction_id))
    tx = result.scalars().first()
    if not tx:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Transaction not found")
    return tx

@router.patch("/{transaction_id}", response_model=TransactionResponse)
@router.put("/{transaction_id}", response_model=TransactionResponse)
async def update_transaction_status(
    transaction_id: uuid.UUID,
    tx_in: TransactionUpdate,
    current_user: User = Depends(get_current_admin_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Update transaction status (Admin only).
    """
    result = await db.execute(select(Transaction).filter(Transaction.id == transaction_id))
    tx = result.scalars().first()
    if not tx:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Transaction not found")

    update_data = tx_in.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(tx, field, value)

    if tx.payment_status == "Completed" and not tx.completed_at:
        tx.completed_at = datetime.now(timezone.utc).replace(tzinfo=None)

    await db.commit()
    await db.refresh(tx)
    return tx

# ==================== Bank Accounts ====================

@router.get("/bank-accounts", response_model=List[BankAccountResponse])
async def list_bank_accounts(
    active_only: bool = True,
    current_user: User = Depends(get_current_admin_user),
    db: AsyncSession = Depends(get_db)
):
    query = select(BankAccount)
    if active_only:
        query = query.filter(BankAccount.is_active == True)
    result = await db.execute(query.order_by(BankAccount.bank_name))
    return result.scalars().all()

@router.post("/bank-accounts", response_model=BankAccountResponse, status_code=status.HTTP_201_CREATED)
async def create_bank_account(
    acc_in: BankAccountCreate,
    current_user: User = Depends(get_current_admin_user),
    db: AsyncSession = Depends(get_db)
):
    db_acc = BankAccount(**acc_in.model_dump())
    db.add(db_acc)
    await db.commit()
    await db.refresh(db_acc)
    return db_acc

@router.get("/bank-accounts/{account_id}", response_model=BankAccountResponse)
async def get_bank_account(
    account_id: uuid.UUID,
    current_user: User = Depends(get_current_admin_user),
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(select(BankAccount).filter(BankAccount.id == account_id))
    acc = result.scalars().first()
    if not acc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Bank account not found")
    return acc

@router.patch("/bank-accounts/{account_id}", response_model=BankAccountResponse)
@router.put("/bank-accounts/{account_id}", response_model=BankAccountResponse)
async def update_bank_account(
    account_id: uuid.UUID,
    acc_in: BankAccountUpdate,
    current_user: User = Depends(get_current_admin_user),
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(select(BankAccount).filter(BankAccount.id == account_id))
    acc = result.scalars().first()
    if not acc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Bank account not found")

    update_data = acc_in.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(acc, field, value)

    acc.updated_at = datetime.now(timezone.utc).replace(tzinfo=None)
    await db.commit()
    await db.refresh(acc)
    return acc

@router.delete("/bank-accounts/{account_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_bank_account(
    account_id: uuid.UUID,
    current_user: User = Depends(get_current_admin_user),
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(select(BankAccount).filter(BankAccount.id == account_id))
    acc = result.scalars().first()
    if not acc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Bank account not found")

    await db.delete(acc)
    await db.commit()

# ==================== Transfers ====================

@router.get("/transfers", response_model=List[TransferResponse])
async def list_transfers(
    current_user: User = Depends(get_current_admin_user),
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(select(Transfer).order_by(Transfer.created_at.desc()))
    return result.scalars().all()

@router.post("/transfers", response_model=TransferResponse, status_code=status.HTTP_201_CREATED)
async def create_transfer(
    transfer_in: TransferCreate,
    current_user: User = Depends(get_current_admin_user),
    db: AsyncSession = Depends(get_db)
):
    acc_res = await db.execute(select(BankAccount).filter(BankAccount.id == transfer_in.destination_account_id))
    if not acc_res.scalars().first():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Destination bank account not found")

    ref = f"TRF-{uuid.uuid4().hex[:8].upper()}"
    db_trf = Transfer(
        **transfer_in.model_dump(),
        initiated_by_id=current_user.id,
        transaction_reference=ref,
        status="Pending",
        created_at=datetime.now(timezone.utc).replace(tzinfo=None)
    )
    db.add(db_trf)
    await db.commit()
    await db.refresh(db_trf)
    return db_trf

# ==================== M-Pesa Callback ====================

@router.post("/mpesa/callback")
async def mpesa_callback(request: Request, db: AsyncSession = Depends(get_db)):
    """
    Handle Daraja M-Pesa IPN / STK callback.
    """
    try:
        body = await request.json()
    except Exception:
        body = {}

    stk_callback = body.get("Body", {}).get("stkCallback", {})
    result_code = stk_callback.get("ResultCode")
    checkout_id = stk_callback.get("CheckoutRequestID")

    # If completed successfully, update transaction
    if result_code == 0 and checkout_id:
        items = stk_callback.get("CallbackMetadata", {}).get("Item", [])
        receipt = next((i.get("Value") for i in items if i.get("Name") == "MpesaReceiptNumber"), None)
        
        tx_res = await db.execute(
            select(Transaction).filter(Transaction.transaction_reference == checkout_id)
        )
        tx = tx_res.scalars().first()
        if tx:
            tx.payment_status = "Completed"
            tx.mpesa_receipt = receipt
            tx.completed_at = datetime.now(timezone.utc).replace(tzinfo=None)
            await db.commit()

    return {"ResultCode": 0, "ResultDesc": "Success"}
