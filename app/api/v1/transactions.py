import uuid
from datetime import datetime, timezone
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Request
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, or_

from app.core.config import settings
from app.db.session import get_db
from app.models.transactions import Transaction, BankAccount, Transfer
from app.models.donations import Donation
from app.models.users import User
from app.schemas.transactions import (
    TransactionCreate, TransactionUpdate, TransactionResponse,
    BankAccountCreate, BankAccountUpdate, BankAccountResponse,
    TransferCreate, TransferResponse
)
from app.api.dependencies.auth import (
    get_current_active_user,
    get_current_admin_user,
    get_optional_current_user
)
from app.services.mpesa import mpesa_service
import logging

logger = logging.getLogger(__name__)

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


# ==================== M-Pesa STK Push & Status Checking ====================

class STKPushInput(BaseModel):
    phone_number: str
    amount: float
    account_name: Optional[str] = "Donation"
    donation: Optional[str] = None
    donation_id: Optional[str] = None


@router.post("/initiate_stk_push")
@router.post("/initiate_stk_push/")
@router.post("/initiate-stk-push")
@router.post("/initiate-stk-push/")
async def initiate_stk_push(
    payload: STKPushInput,
    current_user: Optional[User] = Depends(get_optional_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Initiate Safaricom Daraja M-Pesa STK push for a donation drive.
    """
    # 1. Resolve donation ID (accept either 'donation' or 'donation_id')
    raw_id = payload.donation or payload.donation_id
    if not raw_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Donation ID is required"
        )
    try:
        target_donation_id = uuid.UUID(str(raw_id).strip())
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid donation UUID: {raw_id}"
        )

    # 2. Verify donation exists
    d_res = await db.execute(
        select(Donation).filter(Donation.id == target_donation_id, Donation.is_deleted == False)
    )
    donation = d_res.scalars().first()
    if not donation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Donation drive not found"
        )

    # 3. Format and sanitize phone number (must be 2547XXXXXXXX or 2541XXXXXXXX)
    clean_phone = payload.phone_number.replace("+", "").replace(" ", "").replace("-", "").strip()
    if clean_phone.startswith("0"):
        clean_phone = f"254{clean_phone[1:]}"
    elif clean_phone.startswith("7") or clean_phone.startswith("1"):
        clean_phone = f"254{clean_phone}"

    if len(clean_phone) != 12 or not clean_phone.startswith("254"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid Kenyan phone number: {payload.phone_number}. Must be in 2547XXXXXXXX format."
        )

    # 4. Generate local reference & create Pending Transaction in DB
    ref = f"WS_{uuid.uuid4().hex[:12].upper()}"
    account_name = payload.account_name or donation.title
    db_tx = Transaction(
        donation_id=target_donation_id,
        user_id=current_user.id if current_user else None,
        account_name=account_name[:100],
        account_number=donation.account_number or donation.paybill_number,
        amount=payload.amount,
        payment_method="M-Pesa",
        payment_status="Pending",
        transaction_reference=ref,
        donated_at=datetime.now(timezone.utc).replace(tzinfo=None)
    )
    db.add(db_tx)
    await db.commit()
    await db.refresh(db_tx)

    # 5. Check for custom Daraja credentials per donation or bank account
    party_b = donation.paybill_number
    bank_acc = None
    if party_b:
        b_res = await db.execute(select(BankAccount).filter(BankAccount.paybill_number == party_b, BankAccount.is_active == True))
        bank_acc = b_res.scalars().first()

    consumer_key = donation.consumer_key or (bank_acc.consumer_key if bank_acc else None)
    consumer_secret = donation.consumer_secret or (bank_acc.consumer_secret if bank_acc else None)
    passkey = donation.passkey or (bank_acc.passkey if bank_acc else None)
    if consumer_key and consumer_secret:
        shortcode = party_b or (bank_acc.paybill_number if bank_acc else settings.MPESA_SHORTCODE)
    else:
        consumer_key = None
        consumer_secret = None
        passkey = None
        shortcode = settings.MPESA_SHORTCODE

    # 6. Trigger M-Pesa STK Push
    account_ref = "".join(c for c in (donation.account_number or account_name or "JamiaWaqf") if c.isalnum())[:12]
    trans_desc = f"Donation {donation.title[:15]}"[:30]

    try:
        mpesa_res = await mpesa_service.initiate_stk_push(
            phone_number=clean_phone,
            amount=payload.amount,
            reference=account_ref,
            description=trans_desc,
            shortcode=shortcode,
            passkey=passkey,
            consumer_key=consumer_key,
            consumer_secret=consumer_secret,
        )
    except Exception as e:
        db_tx.payment_status = "Failed"
        await db.commit()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"M-Pesa Gateway Error: {str(e)}"
        )

    # 7. Check for CheckoutRequestID in Safaricom response
    checkout_id = mpesa_res.get("CheckoutRequestID")
    merchant_id = mpesa_res.get("MerchantRequestID", "")
    res_code = str(mpesa_res.get("ResponseCode", "0"))
    res_desc = mpesa_res.get("ResponseDescription", "Success. Request accepted for processing")
    cust_msg = mpesa_res.get("CustomerMessage", "Success. Request accepted for processing")

    if checkout_id:
        db_tx.transaction_reference = checkout_id
        await db.commit()
        await db.refresh(db_tx)
        return {
            "transaction_id": str(db_tx.id),
            "MerchantRequestID": merchant_id,
            "CheckoutRequestID": checkout_id,
            "ResponseCode": res_code,
            "ResponseDescription": res_desc,
            "CustomerMessage": cust_msg,
        }
    else:
        db_tx.payment_status = "Failed"
        await db.commit()
        err_msg = mpesa_res.get("errorMessage", res_desc or "STK push initiation failed")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=err_msg
        )


@router.get("/check_status")
@router.get("/check_status/")
@router.get("/check-status")
@router.get("/check-status/")
async def check_status(reference: str, db: AsyncSession = Depends(get_db)):
    """
    Check payment status by transaction reference or CheckoutRequestID.
    """
    if not reference:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Reference is required")

    # 1. Search by transaction_reference or mpesa_receipt
    result = await db.execute(
        select(Transaction).filter(
            or_(
                Transaction.transaction_reference == reference,
                Transaction.mpesa_receipt == reference
            )
        )
    )
    tx = result.scalars().first()

    # 2. Search by UUID if valid UUID
    if not tx:
        try:
            tx_uuid = uuid.UUID(reference)
            result = await db.execute(select(Transaction).filter(Transaction.id == tx_uuid))
            tx = result.scalars().first()
        except ValueError:
            pass

    if not tx:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Transaction not found")

    # If transaction is still Pending and has an M-Pesa CheckoutRequestID, query Daraja STK query directly
    if tx.payment_status == "Pending" and tx.transaction_reference and tx.transaction_reference.startswith("ws_CO_"):
        try:
            consumer_key = None
            consumer_secret = None
            passkey = None
            shortcode = settings.MPESA_SHORTCODE

            if tx.donation_id:
                don_res = await db.execute(select(Donation).filter(Donation.id == tx.donation_id))
                don = don_res.scalars().first()
                if don:
                    party_b = don.paybill_number
                    bank_acc = None
                    if party_b:
                        b_res = await db.execute(
                            select(BankAccount).filter(BankAccount.paybill_number == party_b, BankAccount.is_active == True)
                        )
                        bank_acc = b_res.scalars().first()
                    consumer_key = don.consumer_key or (bank_acc.consumer_key if bank_acc else None)
                    consumer_secret = don.consumer_secret or (bank_acc.consumer_secret if bank_acc else None)
                    passkey = don.passkey or (bank_acc.passkey if bank_acc else None)
                    if consumer_key and consumer_secret:
                        shortcode = party_b or (bank_acc.paybill_number if bank_acc else settings.MPESA_SHORTCODE)

            stk_res = await mpesa_service.query_stk_status(
                checkout_request_id=tx.transaction_reference,
                shortcode=shortcode,
                passkey=passkey,
                consumer_key=consumer_key,
                consumer_secret=consumer_secret,
            )
            res_code = str(stk_res.get("ResultCode", ""))
            if res_code == "0":
                tx.payment_status = "Completed"
                tx.completed_at = datetime.now(timezone.utc).replace(tzinfo=None)
                await db.commit()
                await db.refresh(tx)
                logger.info(f"Transaction {tx.id} resolved to Completed via Daraja STK Query")
            elif res_code in ("1032", "1037", "2001", "1"):
                tx.payment_status = "Failed"
                await db.commit()
                await db.refresh(tx)
                logger.info(f"Transaction {tx.id} resolved to Failed via Daraja STK Query (code {res_code})")
        except Exception as e:
            logger.warning(f"Error querying Daraja STK Query for {tx.transaction_reference}: {e}")

    return {
        "payment_status": tx.payment_status,
        "mpesa_receipt": tx.mpesa_receipt or "",
        "transaction_id": str(tx.id),
        "amount": float(tx.amount),
    }


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
@router.post("/mpesa/callback/")
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
    result_desc = stk_callback.get("ResultDesc", "")
    checkout_id = stk_callback.get("CheckoutRequestID")
    merchant_id = stk_callback.get("MerchantRequestID")

    logger.info(f"M-Pesa STK Callback received: CheckoutRequestID={checkout_id}, MerchantRequestID={merchant_id}, ResultCode={result_code}, Desc={result_desc}")

    if checkout_id:
        tx_res = await db.execute(
            select(Transaction).filter(
                or_(
                    Transaction.transaction_reference == checkout_id,
                    Transaction.transaction_reference == merchant_id
                )
            )
        )
        tx = tx_res.scalars().first()
        if tx:
            if str(result_code) == "0":
                items = stk_callback.get("CallbackMetadata", {}).get("Item", [])
                receipt = next((i.get("Value") for i in items if i.get("Name") == "MpesaReceiptNumber"), None)
                tx.payment_status = "Completed"
                if receipt:
                    tx.mpesa_receipt = str(receipt)
                tx.completed_at = datetime.now(timezone.utc).replace(tzinfo=None)
                logger.info(f"Transaction {tx.id} marked as Completed. Receipt: {receipt}")
            else:
                tx.payment_status = "Failed"
                logger.info(f"Transaction {tx.id} marked as Failed. Reason: {result_desc}")
            await db.commit()
        else:
            logger.warning(f"Transaction not found for CheckoutRequestID={checkout_id}")

    return {"ResultCode": 0, "ResultDesc": "Success"}
