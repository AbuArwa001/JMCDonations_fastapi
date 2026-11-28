import uuid, logging, time
from typing import Dict, Any, Optional
from datetime import datetime, timezone
from sqlalchemy import select, or_
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import HTTPException
from app.core.config import settings
from app.models.transactions import Transaction, BankAccount
from app.models.donations import Donation
from app.models.users import User
from app.schemas.v1.transactions import STKPushInput
from app.services.mpesa import mpesa_service
from app.services.donation_resolver import resolve_donation, notify_admin_donation_completed, MIN_ADMIN_NOTIFICATION_AMOUNT
logger = logging.getLogger(__name__)

class STKService:
    def __init__(self):
        self.stk_results: Dict[str, Dict[str, Any]] = {}
        self.last_query_time: Dict[str, float] = {}

    async def initiate_stk_push(self, db: AsyncSession, payload: STKPushInput, user: Optional[User]) -> Dict[str, Any]:
        donation = await resolve_donation(db, payload.donation or payload.donation_id)
        now = datetime.now(timezone.utc).replace(tzinfo=None)
        if donation.status != "Active" or (donation.end_date and donation.end_date < now):
            raise HTTPException(status_code=400, detail="This donation drive is closed and no longer accepting contributions.")
        clean_p = payload.phone_number.replace("+", "").replace(" ", "").replace("-", "").strip()
        if clean_p.startswith("0"): clean_p = f"254{clean_p[1:]}"
        elif clean_p.startswith("7") or clean_p.startswith("1"): clean_p = f"254{clean_p}"
        if len(clean_p) != 12 or not clean_p.startswith("254"):
            raise HTTPException(status_code=400, detail=f"Invalid Kenyan phone number: {payload.phone_number}.")
        target_uid = user.id if user else None
        if not target_uid and payload.user_id:
            try: target_uid = uuid.UUID(str(payload.user_id).strip())
            except ValueError: pass
        if not target_uid:
            matched = (await db.execute(select(User).filter(User.phone_number.contains(clean_p[-9:])))).scalars().first()
            if matched: target_uid = matched.id; user = matched
        donor_name = user.full_name if (user and user.full_name) else (payload.account_name or "Anonymous")
        tx = Transaction(donation_id=donation.id, user_id=target_uid, account_name=donor_name[:100], account_number=clean_p, amount=payload.amount, payment_method="M-Pesa", payment_status="Pending", transaction_reference=f"WS_{uuid.uuid4().hex[:12].upper()}", donated_at=now)
        db.add(tx); await db.commit(); await db.refresh(tx)
        bank_acc = None
        if donation.paybill_number:
            bank_acc = (await db.execute(select(BankAccount).filter(BankAccount.paybill_number == donation.paybill_number, BankAccount.is_active == True))).scalars().first()
        ck = donation.consumer_key or (bank_acc.consumer_key if bank_acc else None)
        cs = donation.consumer_secret or (bank_acc.consumer_secret if bank_acc else None)
        pk = donation.passkey or (bank_acc.passkey if bank_acc else None)
        sc = donation.paybill_number or (bank_acc.paybill_number if bank_acc else settings.MPESA_SHORTCODE) if (ck and cs) else settings.MPESA_SHORTCODE
        acc_ref = "JamiaZakat" if "zakat" in (donation.title or "").lower() else (donation.account_name or "JamiaWaqf")[:12]
        try:
            res = await mpesa_service.initiate_stk_push(phone_number=clean_p, amount=payload.amount, reference=acc_ref, description=f"Donation {acc_ref}"[:30], shortcode=sc, passkey=pk, consumer_key=ck, consumer_secret=cs)
        except Exception as e:
            tx.payment_status = "Failed"; await db.commit()
            raise HTTPException(status_code=400, detail=f"M-Pesa Gateway Error: {str(e)}")
        cid = res.get("CheckoutRequestID")
        if not cid:
            tx.payment_status = "Failed"; await db.commit()
            raise HTTPException(status_code=400, detail=res.get("errorMessage", "STK push initiation failed"))
        tx.transaction_reference = cid; await db.commit(); await db.refresh(tx)
        return {"transaction_id": str(tx.id), "MerchantRequestID": res.get("MerchantRequestID", ""), "CheckoutRequestID": cid, "ResponseCode": str(res.get("ResponseCode", "0")), "ResponseDescription": res.get("ResponseDescription", ""), "CustomerMessage": res.get("CustomerMessage", "")}

    async def check_status(self, db: AsyncSession, reference: str) -> Dict[str, Any]:
        if not reference: raise HTTPException(status_code=400, detail="Reference is required")
        tx = (await db.execute(select(Transaction).filter(or_(Transaction.transaction_reference == reference, Transaction.mpesa_receipt == reference)))).scalars().first()
        if not tx:
            try: tx = (await db.execute(select(Transaction).filter(Transaction.id == uuid.UUID(reference)))).scalars().first()
            except ValueError: pass
        if not tx: raise HTTPException(status_code=404, detail="Transaction not found")
        cid, now_ts = tx.transaction_reference or "", time.time()
        now = datetime.now(timezone.utc).replace(tzinfo=None)
        age = (now - tx.donated_at).total_seconds() if tx.donated_at else 99
        last_q = self.last_query_time.get(cid, 0)
        if tx.payment_status == "Pending" and cid.startswith("ws_CO_") and age >= 10 and (now_ts - last_q >= 10):
            self.last_query_time[cid] = now_ts
            try:
                stk = await mpesa_service.query_stk_status(checkout_request_id=cid, shortcode=settings.MPESA_SHORTCODE)
                code, desc = str(stk.get("ResultCode", "")), str(stk.get("ResultDesc", ""))
                if code == "0":
                    tx.payment_status = "Completed"; tx.completed_at = now
                    await db.commit(); await db.refresh(tx)
                    if (tx.amount or 0) >= MIN_ADMIN_NOTIFICATION_AMOUNT:
                        d = (await db.execute(select(Donation).filter(Donation.id == tx.donation_id))).scalars().first()
                        notify_admin_donation_completed(tx, d)
                elif code == "1032":
                    tx.payment_status = "Cancelled"; self.stk_results[cid] = {"result_code": code, "result_desc": desc}
                    await db.commit(); await db.refresh(tx)
                elif code in ("1037", "2001", "1"):
                    tx.payment_status = "Failed"; self.stk_results[cid] = {"result_code": code, "result_desc": desc}
                    await db.commit(); await db.refresh(tx)
            except Exception as e:
                if "429" in str(e): logger.debug(f"Daraja query rate-limited for {cid}; awaiting callback.")
                else: logger.warning(f"Error querying Daraja STK: {e}")
        stk_info = self.stk_results.get(cid) or self.stk_results.get(str(tx.id)) or {}
        return {"payment_status": tx.payment_status, "mpesa_receipt": tx.mpesa_receipt or "", "transaction_id": str(tx.id), "amount": float(tx.amount), "result_code": stk_info.get("result_code"), "result_desc": stk_info.get("result_desc")}

stk_service = STKService()
