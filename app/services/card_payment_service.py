import uuid
from typing import Dict, Any, Optional
from datetime import datetime, timezone
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import HTTPException, status

from app.core.config import settings
from app.models.transactions import Transaction
from app.models.users import User
from app.schemas.v1.transactions import CardPaymentInput, FlutterwaveVerifyInput
from app.services.donation_resolver import resolve_donation


class CardPaymentService:
    async def initiate_card(self, db: AsyncSession, payload: CardPaymentInput, user: Optional[User]) -> Dict[str, Any]:
        donation = await resolve_donation(db, payload.donation_id or payload.donation)
        ref = f"JM-{uuid.uuid4()}"
        donor = user.full_name if user else "Anonymous"
        tx = Transaction(
            donation_id=donation.id, user_id=user.id if user else None,
            account_name=donor[:100], account_number="Card", amount=payload.amount,
            payment_method="Card", payment_status="Pending", transaction_reference=ref,
            donated_at=datetime.now(timezone.utc).replace(tzinfo=None)
        )
        db.add(tx); await db.commit(); await db.refresh(tx)
        return {
            "message": "Card payment initiated", "tx_ref": tx.transaction_reference,
            "public_key": settings.FLUTTERWAVE_PUBLIC_KEY, "amount": float(tx.amount),
            "currency": "KES", "transaction_id": str(tx.id)
        }

    async def verify_flutterwave(self, db: AsyncSession, payload: FlutterwaveVerifyInput, user: Optional[User]) -> Dict[str, Any]:
        if not payload.tx_ref:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Missing tx_ref")
        res = await db.execute(select(Transaction).filter(Transaction.transaction_reference == payload.tx_ref))
        tx = res.scalars().first()
        if not tx:
            donation = await resolve_donation(db, payload.donation_id)
            tx = Transaction(
                transaction_reference=payload.tx_ref, donation_id=donation.id, amount=payload.amount or 0.0,
                payment_method="Card", payment_status="Pending", user_id=user.id if user else None,
                account_number="Card", donated_at=datetime.now(timezone.utc).replace(tzinfo=None)
            )
            db.add(tx); await db.commit(); await db.refresh(tx)

        if tx.payment_status == "Completed":
            return {"message": "Transaction already processed", "transaction_id": str(tx.id), "status": tx.payment_status}

        status_param = (payload.status or "successful").lower()
        if status_param in ("successful", "completed", "success"):
            tx.payment_status = "Completed"
            tx.mpesa_receipt = payload.flw_ref or ""
            tx.completed_at = datetime.now(timezone.utc).replace(tzinfo=None)
        else:
            tx.payment_status = "Failed"
        await db.commit(); await db.refresh(tx)
        return {"message": "Transaction updated successfully", "transaction_id": str(tx.id), "status": tx.payment_status}


card_payment_service = CardPaymentService()
