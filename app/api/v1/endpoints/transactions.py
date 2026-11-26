import uuid
import logging
from typing import List, Optional, Any, Dict, Union
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, status, Query, Request
from fastapi.responses import RedirectResponse
from sqlalchemy import select, or_
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db, require_permission, get_optional_current_user
from app.core.config import settings
from app.repositories.transaction_repo import TransactionRepository
from app.services.transaction_service import TransactionService
from app.services.mpesa import mpesa_service
from app.services.paypal import paypal_service
from app.services.firebase import firebase_service
from app.models.transactions import Transaction, BankAccount
from app.models.donations import Donation
from app.models.users import User
from app.models.khutba import NotificationLog
from app.schemas.v1.transactions import (
    TransactionResponse, TransactionUpdate, BulkDeleteTransactionsRequest,
    BulkDeleteTransactionsResponse, STKPushRequest, STKPushInput,
    PayPalInitInput, CardPaymentInput, FlutterwaveVerifyInput
)

logger = logging.getLogger(__name__)
router = APIRouter()

# In-memory store for recent STK Push result descriptions/codes (e.g. cancellation, insufficient funds)
_stk_results: Dict[str, Dict[str, Any]] = {}

MIN_ADMIN_DONATION_NOTIFICATION_AMOUNT = 10000


def _notify_admin_donation_completed(tx: Transaction, donation: Optional[Donation] = None, user: Optional[User] = None) -> None:
    """Send FCM to admins topic when a donation payment completes (10,000 KES and above)."""
    if (tx.amount or 0) < MIN_ADMIN_DONATION_NOTIFICATION_AMOUNT:
        return

    drive_title = donation.title if donation else "a donation drive"
    if user and user.full_name:
        donor = user.full_name
    elif tx.account_name and tx.account_name != drive_title and tx.account_name.lower() != "donation":
        donor = tx.account_name
    else:
        donor = tx.account_number or "A donor"
    title = "💰 New Donation Received"
    body = f"{donor} donated KES {tx.amount:,.0f} to '{drive_title}'."
    data = {
        "type": "admin_donation",
        "transaction_id": str(tx.id),
        "amount": str(tx.amount),
        "donation_id": str(tx.donation_id) if tx.donation_id else "",
    }
    try:
        firebase_service.send_topic_notification("admins", title, body, data=data)
        logger.info(f"Admin FCM sent for completed transaction {tx.id}")
    except Exception as e:
        logger.error(f"Failed to send admin FCM for tx {tx.id}: {e}")


async def _resolve_donation(db: AsyncSession, raw_id: Any) -> Donation:
    """Resolve donation record by UUID or alias ('zakat_al_mal', 'general', etc.)."""
    if not raw_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Donation ID is required"
        )
    raw_str = str(raw_id).strip()
    is_zakat_alias = raw_str.lower() in ["zakat_al_mal", "zakat", "zakat-al-mal", "zakat_ul_mal"]
    is_general_alias = raw_str.lower() in ["general", "general_donation", "general-donation"]

    if is_zakat_alias:
        z_res = await db.execute(
            select(Donation).filter(
                Donation.title.ilike("%zakat%"),
                Donation.status == "Active",
                Donation.is_deleted == False
            )
        )
        found = z_res.scalars().first()
        if not found:
            f_res = await db.execute(
                select(Donation).filter(Donation.status == "Active", Donation.is_deleted == False)
            )
            found = f_res.scalars().first()
        if found:
            return found

    if is_general_alias:
        f_res = await db.execute(
            select(Donation).filter(Donation.status == "Active", Donation.is_deleted == False)
        )
        found = f_res.scalars().first()
        if found:
            return found

    try:
        target_donation_id = uuid.UUID(raw_str)
    except ValueError:
        t_res = await db.execute(
            select(Donation).filter(
                Donation.title.ilike(f"%{raw_str}%"),
                Donation.status == "Active",
                Donation.is_deleted == False
            )
        )
        found = t_res.scalars().first()
        if found:
            return found
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid donation UUID: {raw_id}"
        )

    d_res = await db.execute(
        select(Donation).filter(Donation.id == target_donation_id, Donation.is_deleted == False)
    )
    donation = d_res.scalars().first()
    if not donation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Donation drive not found"
        )
    return donation


# ==================== Mobile Payment Endpoints ====================

@router.post("/initiate_stk_push")
@router.post("/initiate_stk_push/", include_in_schema=False)
@router.post("/initiate-stk-push", include_in_schema=False)
@router.post("/initiate-stk-push/", include_in_schema=False)
async def initiate_stk_push(
    payload: STKPushInput,
    current_user: Optional[User] = Depends(get_optional_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Initiate Safaricom Daraja M-Pesa STK push for a donation drive."""
    raw_id = payload.donation or payload.donation_id
    donation = await _resolve_donation(db, raw_id)
    target_donation_id = donation.id

    now = datetime.now(timezone.utc).replace(tzinfo=None)
    is_past_due = donation.end_date is not None and donation.end_date < now
    if donation.status != "Active" or is_past_due:
        if donation.status == "Active" and is_past_due:
            donation.status = "Closed"
            await db.commit()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="This donation drive is closed and no longer accepting contributions."
        )

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

    target_user_id = current_user.id if current_user else None
    if not target_user_id and payload.user_id:
        try:
            target_user_id = uuid.UUID(str(payload.user_id).strip())
        except ValueError:
            target_user_id = None

    if not target_user_id:
        u_phone_res = await db.execute(
            select(User).filter(User.phone_number.contains(clean_phone[-9:]))
        )
        matched_user = u_phone_res.scalars().first()
        if matched_user:
            target_user_id = matched_user.id
            if not current_user:
                current_user = matched_user

    ref = f"WS_{uuid.uuid4().hex[:12].upper()}"
    raw_payload_name = payload.account_name or ""
    if current_user and current_user.full_name:
        donor_account_name = current_user.full_name
    elif (
        raw_payload_name
        and raw_payload_name.lower() != "donation"
        and raw_payload_name != donation.title
    ):
        donor_account_name = raw_payload_name
    else:
        donor_account_name = "Anonymous"

    db_tx = Transaction(
        donation_id=target_donation_id,
        user_id=target_user_id,
        account_name=donor_account_name[:100],
        account_number=clean_phone,
        amount=payload.amount,
        payment_method="M-Pesa",
        payment_status="Pending",
        transaction_reference=ref,
        donated_at=datetime.now(timezone.utc).replace(tzinfo=None)
    )
    db.add(db_tx)
    await db.commit()
    await db.refresh(db_tx)

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

    raw_id_str = str(payload.donation or payload.donation_id or "").strip().lower()
    is_zakat = (
        raw_id_str in ["zakat_al_mal", "zakat", "zakat-al-mal", "zakat_ul_mal"]
        or "zakat" in (donation.title or "").lower()
        or (payload.account_name or "").strip().lower() == "jamiazakat"
    )

    if is_zakat:
        account_ref = "JamiaZakat"
    else:
        raw_account_ref = (
            (donation.account_name.strip() if donation.account_name and donation.account_name.strip() else None)
            or (donation.account_number.strip() if donation.account_number and donation.account_number.strip() else None)
            or (payload.account_name.strip() if payload.account_name and payload.account_name.strip().lower() != "donation" and payload.account_name.strip() != donation.title else None)
            or (donor_account_name if donor_account_name and donor_account_name != "Anonymous" and donor_account_name != donation.title else None)
            or "JamiaWaqf"
        )
        account_ref = "".join(c for c in raw_account_ref if c.isalnum() or c in "-_")[:12].strip() or "JamiaWaqf"
    trans_desc = f"Donation {account_ref}"[:30]

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
@router.get("/check_status/", include_in_schema=False)
@router.get("/check-status", include_in_schema=False)
@router.get("/check-status/", include_in_schema=False)
async def check_status(reference: str, db: AsyncSession = Depends(get_db)):
    """Check payment status by transaction reference or CheckoutRequestID."""
    if not reference:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Reference is required")

    result = await db.execute(
        select(Transaction).filter(
            or_(
                Transaction.transaction_reference == reference,
                Transaction.mpesa_receipt == reference
            )
        )
    )
    tx = result.scalars().first()

    if not tx:
        try:
            tx_uuid = uuid.UUID(reference)
            result = await db.execute(select(Transaction).filter(Transaction.id == tx_uuid))
            tx = result.scalars().first()
        except ValueError:
            pass

    if not tx:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Transaction not found")

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
            res_desc = str(stk_res.get("ResultDesc", ""))
            if res_code == "0":
                tx.payment_status = "Completed"
                tx.completed_at = datetime.now(timezone.utc).replace(tzinfo=None)
                await db.commit()
                await db.refresh(tx)
                logger.info(f"Transaction {tx.id} resolved to Completed via Daraja STK Query")
                if (tx.amount or 0) >= MIN_ADMIN_DONATION_NOTIFICATION_AMOUNT:
                    don_res = await db.execute(select(Donation).filter(Donation.id == tx.donation_id))
                    donation_obj = don_res.scalars().first()
                    _notify_admin_donation_completed(tx, donation_obj)
                    log = NotificationLog(
                        title="💰 New Donation Received",
                        body=f"KES {tx.amount:,.0f} donated to '{donation_obj.title if donation_obj else 'a drive'}'.",
                        notification_type="admin_donation",
                        related_donation_id=str(tx.donation_id) if tx.donation_id else None,
                        recipient_count=1,
                    )
                    db.add(log)
                    await db.commit()
            elif res_code == "1032":
                tx.payment_status = "Cancelled"
                _stk_results[tx.transaction_reference] = {
                    "result_code": res_code,
                    "result_desc": res_desc or "Request cancelled by user."
                }
                await db.commit()
                await db.refresh(tx)
                logger.info(f"Transaction {tx.id} resolved to Cancelled via Daraja STK Query")
            elif res_code in ("1037", "2001", "1"):
                tx.payment_status = "Failed"
                _stk_results[tx.transaction_reference] = {
                    "result_code": res_code,
                    "result_desc": res_desc
                }
                await db.commit()
                await db.refresh(tx)
                logger.info(f"Transaction {tx.id} resolved to Failed via Daraja STK Query (code {res_code}: {res_desc})")
        except Exception as e:
            logger.warning(f"Error querying Daraja STK Query for {tx.transaction_reference}: {e}")

    stk_info = _stk_results.get(tx.transaction_reference or "") or _stk_results.get(str(tx.id)) or {}
    final_res_code = stk_info.get("result_code")
    final_res_desc = stk_info.get("result_desc")

    if tx.payment_status == "Cancelled" and not final_res_code:
        final_res_code = "1032"
        final_res_desc = "Request cancelled by user."

    return {
        "payment_status": tx.payment_status,
        "mpesa_receipt": tx.mpesa_receipt or "",
        "transaction_id": str(tx.id),
        "amount": float(tx.amount),
        "result_code": final_res_code,
        "result_desc": final_res_desc,
    }


@router.post("/initiate_paypal_payment")
@router.post("/initiate_paypal_payment/", include_in_schema=False)
@router.post("/initiate-paypal-payment", include_in_schema=False)
@router.post("/initiate-paypal-payment/", include_in_schema=False)
async def initiate_paypal_payment(
    payload: PayPalInitInput,
    current_user: Optional[User] = Depends(get_optional_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Initiate a PayPal donation by creating an order and returning the approval URL."""
    raw_id = payload.donation or payload.donation_id
    donation = await _resolve_donation(db, raw_id)
    target_donation_id = donation.id

    raw_paypal_name = payload.account_name or ""
    if current_user and current_user.full_name:
        donor_account_name = current_user.full_name
    elif (
        raw_paypal_name
        and raw_paypal_name.lower() != "donation"
        and raw_paypal_name != donation.title
    ):
        donor_account_name = raw_paypal_name
    else:
        donor_account_name = "Anonymous"

    db_tx = Transaction(
        donation_id=target_donation_id,
        user_id=current_user.id if current_user else None,
        account_name=donor_account_name[:100],
        account_number="PayPal",
        amount=payload.amount,
        payment_method="Paypal",
        payment_status="Pending",
        transaction_reference=f"PP_{uuid.uuid4().hex[:12].upper()}",
        donated_at=datetime.now(timezone.utc).replace(tzinfo=None),
    )
    db.add(db_tx)
    await db.commit()
    await db.refresh(db_tx)

    base_callback = settings.PAYPAL_CALLBACK_URL.rstrip("/")
    return_url = f"{base_callback}/?tx_id={db_tx.id}"
    cancel_url = f"{base_callback}/?cancel=true&tx_id={db_tx.id}"

    order = await paypal_service.create_order(
        amount=payload.amount,
        currency=payload.currency or "USD",
        return_url=return_url,
        cancel_url=cancel_url,
    )

    if order and "id" in order:
        db_tx.transaction_reference = order["id"]
        await db.commit()
        await db.refresh(db_tx)

        approval_link = next(
            (link["href"] for link in order.get("links", []) if link.get("rel") == "approve"),
            None,
        )
        if approval_link:
            return {
                "approval_url": approval_link,
                "transaction_id": str(db_tx.id),
            }

    db_tx.payment_status = "Failed"
    await db.commit()
    raise HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail="Failed to create PayPal order",
    )


@router.get("/paypal_callback")
@router.get("/paypal_callback/", include_in_schema=False)
@router.get("/paypal-callback", include_in_schema=False)
@router.get("/paypal-callback/", include_in_schema=False)
async def paypal_callback(
    tx_id: Optional[str] = None,
    token: Optional[str] = None,
    cancel: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
):
    """Handle return redirect from PayPal approval or cancellation."""
    tx = None
    if tx_id:
        try:
            tx_uuid = uuid.UUID(tx_id.strip())
            t_res = await db.execute(select(Transaction).filter(Transaction.id == tx_uuid))
            tx = t_res.scalars().first()
        except ValueError:
            pass

    if not tx and token:
        t_res = await db.execute(select(Transaction).filter(Transaction.transaction_reference == token))
        tx = t_res.scalars().first()

    if not tx:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Transaction not found")

    if cancel == "true":
        tx.payment_status = "Failed"
        await db.commit()
        return RedirectResponse(url="jamiamosque://payment/cancel", status_code=status.HTTP_302_FOUND)

    capture_token = token or tx.transaction_reference
    capture = await paypal_service.capture_order(capture_token)

    if capture and capture.get("status") == "COMPLETED":
        tx.payment_status = "Completed"
        tx.completed_at = datetime.now(timezone.utc).replace(tzinfo=None)
        try:
            cap_id = capture["purchase_units"][0]["payments"]["captures"][0]["id"]
            tx.mpesa_receipt = cap_id
        except (KeyError, IndexError):
            tx.mpesa_receipt = capture_token
        await db.commit()

        if (tx.amount or 0) >= MIN_ADMIN_DONATION_NOTIFICATION_AMOUNT:
            don_res = await db.execute(select(Donation).filter(Donation.id == tx.donation_id))
            donation_obj = don_res.scalars().first()
            _notify_admin_donation_completed(tx, donation_obj)
            log = NotificationLog(
                title="💰 New Donation Received (PayPal)",
                body=f"KES {tx.amount:,.0f} donated to '{donation_obj.title if donation_obj else 'a drive'}' via PayPal.",
                notification_type="admin_donation",
                related_donation_id=str(tx.donation_id) if tx.donation_id else None,
                recipient_count=1,
            )
            db.add(log)
            await db.commit()
        return RedirectResponse(
            url=f"jamiamosque://payment/success?tx_id={tx.id}",
            status_code=status.HTTP_302_FOUND,
        )

    tx.payment_status = "Failed"
    await db.commit()
    return RedirectResponse(url="jamiamosque://payment/failure", status_code=status.HTTP_302_FOUND)


@router.post("/initiate_card_payment", status_code=status.HTTP_201_CREATED)
@router.post("/initiate_card_payment/", status_code=status.HTTP_201_CREATED, include_in_schema=False)
@router.post("/initiate-card-payment", status_code=status.HTTP_201_CREATED, include_in_schema=False)
@router.post("/initiate-card-payment/", status_code=status.HTTP_201_CREATED, include_in_schema=False)
async def initiate_card_payment(
    payload: CardPaymentInput,
    current_user: Optional[User] = Depends(get_optional_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Initiate a card payment by creating a pending transaction and returning tx_ref and public key."""
    raw_id = payload.donation_id or payload.donation
    donation = await _resolve_donation(db, raw_id)
    target_donation_id = donation.id

    ref = f"JM-{uuid.uuid4()}"
    donor_account_name = current_user.full_name if current_user else "Anonymous"
    db_tx = Transaction(
        donation_id=target_donation_id,
        user_id=current_user.id if current_user else None,
        account_name=donor_account_name[:100],
        account_number="Card",
        amount=payload.amount,
        payment_method="Card",
        payment_status="Pending",
        transaction_reference=ref,
        donated_at=datetime.now(timezone.utc).replace(tzinfo=None),
    )
    db.add(db_tx)
    await db.commit()
    await db.refresh(db_tx)

    return {
        "message": "Card payment initiated",
        "tx_ref": db_tx.transaction_reference,
        "public_key": settings.FLUTTERWAVE_PUBLIC_KEY,
        "amount": float(db_tx.amount),
        "currency": "KES",
        "transaction_id": str(db_tx.id),
    }


@router.post("/verify_flutterwave_payment")
@router.post("/verify_flutterwave_payment/", include_in_schema=False)
@router.post("/verify-flutterwave-payment", include_in_schema=False)
@router.post("/verify-flutterwave-payment/", include_in_schema=False)
async def verify_flutterwave_payment(
    payload: FlutterwaveVerifyInput,
    current_user: Optional[User] = Depends(get_optional_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Endpoint called by the client after card/Flutterwave charge to verify and persist transaction status."""
    tx_ref = payload.tx_ref
    flw_ref = payload.flw_ref or ""
    status_param = (payload.status or "successful").lower()

    if not tx_ref:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Missing tx_ref")

    result = await db.execute(select(Transaction).filter(Transaction.transaction_reference == tx_ref))
    tx = result.scalars().first()

    if not tx:
        raw_id = payload.donation_id
        donation = await _resolve_donation(db, raw_id)
        target_donation_id = donation.id

        tx = Transaction(
            transaction_reference=tx_ref,
            donation_id=target_donation_id,
            amount=payload.amount or 0.0,
            payment_method="Card",
            payment_status="Pending",
            user_id=current_user.id if current_user else None,
            account_number="Card",
            donated_at=datetime.now(timezone.utc).replace(tzinfo=None),
        )
        db.add(tx)
        await db.commit()
        await db.refresh(tx)

    if tx.payment_status == "Completed":
        return {
            "message": "Transaction already processed",
            "transaction_id": str(tx.id),
            "status": tx.payment_status,
        }

    if status_param in ("successful", "completed", "success"):
        tx.payment_status = "Completed"
        tx.mpesa_receipt = flw_ref
        tx.completed_at = datetime.now(timezone.utc).replace(tzinfo=None)
    else:
        tx.payment_status = "Failed"

    await db.commit()
    await db.refresh(tx)

    return {
        "message": "Transaction updated successfully",
        "transaction_id": str(tx.id),
        "status": tx.payment_status,
    }


@router.post("/mpesa/callback")
@router.post("/mpesa/callback/")
async def mpesa_callback(request: Request, db: AsyncSession = Depends(get_db)):
    """Handle Daraja M-Pesa IPN / STK callback."""
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
                phone = next((i.get("Value") for i in items if i.get("Name") == "PhoneNumber"), None)
                tx.payment_status = "Completed"
                if receipt:
                    tx.mpesa_receipt = str(receipt)
                if phone:
                    clean_p = str(phone).strip()
                    tx.account_number = clean_p
                    if not tx.user_id:
                        u_res = await db.execute(
                            select(User).filter(User.phone_number.contains(clean_p[-9:]))
                        )
                        matched = u_res.scalars().first()
                        if matched:
                            tx.user_id = matched.id
                            logger.info(f"Transaction {tx.id} auto-linked to user {matched.email} ({matched.id})")
                tx.completed_at = datetime.now(timezone.utc).replace(tzinfo=None)
                logger.info(f"Transaction {tx.id} marked as Completed. Receipt: {receipt}")
            elif str(result_code) == "1032":
                tx.payment_status = "Cancelled"
                _stk_results[checkout_id] = {
                    "result_code": str(result_code),
                    "result_desc": result_desc or "Request cancelled by user."
                }
                logger.info(f"Transaction {tx.id} marked as Cancelled by user.")
            else:
                tx.payment_status = "Failed"
                _stk_results[checkout_id] = {
                    "result_code": str(result_code),
                    "result_desc": result_desc
                }
                logger.info(f"Transaction {tx.id} marked as Failed. Reason: {result_desc}")
            await db.commit()

            if str(result_code) == "0" and tx.user_id:
                user_res = await db.execute(select(User).filter(User.id == tx.user_id))
                user_obj = user_res.scalars().first()
                if user_obj and user_obj.fcm_token:
                    try:
                        firebase_service.send_notification(
                            "Donation Successful 🎉",
                            f"Your donation of KES {tx.amount:,.0f} was received. JazakAllahu Khayran!",
                            user_obj.fcm_token
                        )
                        logger.info(f"FCM sent to donor {user_obj.email} for tx {tx.id}")
                    except Exception as e:
                        logger.error(f"Failed to send donor FCM for tx {tx.id}: {e}")

            if str(result_code) == "0" and (tx.amount or 0) >= MIN_ADMIN_DONATION_NOTIFICATION_AMOUNT:
                don_res = await db.execute(select(Donation).filter(Donation.id == tx.donation_id))
                donation_obj = don_res.scalars().first()
                _notify_admin_donation_completed(tx, donation_obj)
                log = NotificationLog(
                    title="💰 New Donation Received",
                    body=f"KES {tx.amount:,.0f} donated to '{donation_obj.title if donation_obj else 'a drive'}' via M-Pesa.",
                    notification_type="admin_donation",
                    related_donation_id=str(tx.donation_id) if tx.donation_id else None,
                    recipient_count=1,
                )
                db.add(log)
                await db.commit()
        else:
            logger.warning(f"Transaction not found for CheckoutRequestID={checkout_id}")

    return {"ResultCode": 0, "ResultDesc": "Success"}


# ==================== Standard CRUD & Management ====================

@router.get("/", response_model=List[TransactionResponse])
@router.get("", response_model=List[TransactionResponse], include_in_schema=False)
async def list_transactions(
    skip: int = Query(0, ge=0), limit: int = Query(50, ge=1, le=100),
    donation_id: Optional[uuid.UUID] = None, status: Optional[str] = None,
    payment_method: Optional[str] = None, search: Optional[str] = None,
    current_user=Depends(require_permission("donations.view")), db: AsyncSession = Depends(get_db)
):
    repo = TransactionRepository(db)
    items, _ = await repo.search(skip=skip, limit=limit, donation_id=donation_id, status=status, payment_method=payment_method, search_query=search)
    return items


@router.post("/bulk-delete", response_model=BulkDeleteTransactionsResponse)
@router.post("/bulk-delete/", response_model=BulkDeleteTransactionsResponse, include_in_schema=False)
async def bulk_delete_transactions(req: BulkDeleteTransactionsRequest, current_user=Depends(require_permission("donations.delete")), db: AsyncSession = Depends(get_db)):
    count = await TransactionRepository(db).bulk_delete(req.transaction_ids)
    await db.commit()
    return BulkDeleteTransactionsResponse(deleted_count=count, message=f"Successfully deleted {count} transactions")


@router.post("/verify-cash/{id}", response_model=TransactionResponse)
async def verify_cash_transaction(id: uuid.UUID, current_user=Depends(require_permission("donations.manage")), db: AsyncSession = Depends(get_db)):
    return await TransactionService(db).verify_cash(id, current_user.id)


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


@router.delete("/{id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_transaction(id: uuid.UUID, current_user=Depends(require_permission("donations.delete")), db: AsyncSession = Depends(get_db)):
    repo = TransactionRepository(db)
    tx = await repo.get_by_id(id)
    if not tx:
        raise HTTPException(status_code=404, detail="Transaction not found")
    await repo.delete(tx)
    await db.commit()
