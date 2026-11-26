import uuid
from typing import Dict, Any, Optional
from datetime import datetime, timezone
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import HTTPException, status
from fastapi.responses import RedirectResponse

from app.core.config import settings
from app.models.transactions import Transaction
from app.models.donations import Donation
from app.models.users import User
from app.schemas.v1.transactions import PayPalInitInput
from app.services.paypal import paypal_service
from app.services.donation_resolver import resolve_donation, notify_admin_donation_completed, MIN_ADMIN_NOTIFICATION_AMOUNT


class PayPalPaymentService:
    async def initiate_paypal(self, db: AsyncSession, payload: PayPalInitInput, user: Optional[User]) -> Dict[str, Any]:
        donation = await resolve_donation(db, payload.donation or payload.donation_id)
        donor = user.full_name if (user and user.full_name) else (payload.account_name or "Anonymous")
        tx = Transaction(
            donation_id=donation.id, user_id=user.id if user else None, account_name=donor[:100],
            account_number="PayPal", amount=payload.amount, payment_method="Paypal", payment_status="Pending",
            transaction_reference=f"PP_{uuid.uuid4().hex[:12].upper()}", donated_at=datetime.now(timezone.utc).replace(tzinfo=None)
        )
        db.add(tx); await db.commit(); await db.refresh(tx)

        base_cb = settings.PAYPAL_CALLBACK_URL.rstrip("/")
        order = await paypal_service.create_order(
            amount=payload.amount, currency=payload.currency or "USD",
            return_url=f"{base_cb}/?tx_id={tx.id}", cancel_url=f"{base_cb}/?cancel=true&tx_id={tx.id}"
        )
        if order and "id" in order:
            tx.transaction_reference = order["id"]
            await db.commit(); await db.refresh(tx)
            link = next((l["href"] for l in order.get("links", []) if l.get("rel") == "approve"), None)
            if link:
                return {"approval_url": link, "transaction_id": str(tx.id)}
        tx.payment_status = "Failed"; await db.commit()
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Failed to create PayPal order")

    async def handle_callback(self, db: AsyncSession, tx_id: Optional[str], token: Optional[str], cancel: Optional[str]) -> RedirectResponse:
        tx = None
        if tx_id:
            try: tx = (await db.execute(select(Transaction).filter(Transaction.id == uuid.UUID(tx_id.strip())))).scalars().first()
            except ValueError: pass
        if not tx and token:
            tx = (await db.execute(select(Transaction).filter(Transaction.transaction_reference == token))).scalars().first()
        if not tx:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Transaction not found")

        if cancel == "true":
            tx.payment_status = "Failed"; await db.commit()
            return RedirectResponse(url="jamiamosque://payment/cancel", status_code=status.HTTP_302_FOUND)

        capture = await paypal_service.capture_order(token or tx.transaction_reference)
        if capture and capture.get("status") == "COMPLETED":
            tx.payment_status = "Completed"; tx.completed_at = datetime.now(timezone.utc).replace(tzinfo=None)
            try: tx.mpesa_receipt = capture["purchase_units"][0]["payments"]["captures"][0]["id"]
            except (KeyError, IndexError): tx.mpesa_receipt = token or tx.transaction_reference
            await db.commit()
            if (tx.amount or 0) >= MIN_ADMIN_NOTIFICATION_AMOUNT:
                d = (await db.execute(select(Donation).filter(Donation.id == tx.donation_id))).scalars().first()
                notify_admin_donation_completed(tx, d)
            return RedirectResponse(url=f"jamiamosque://payment/success?tx_id={tx.id}", status_code=status.HTTP_302_FOUND)

        tx.payment_status = "Failed"; await db.commit()
        return RedirectResponse(url="jamiamosque://payment/failure", status_code=status.HTTP_302_FOUND)


paypal_payment_service = PayPalPaymentService()
