import uuid
from typing import Optional, Dict, Any
from datetime import datetime, timezone
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import HTTPException, status
from app.models.transactions import Transaction
from app.models.donations import Donation
from app.repositories.transaction_repo import TransactionRepository
from app.services.mpesa import mpesa_service
from app.schemas.v1.transactions import TransactionCreate, TransactionResponse

class TransactionService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.repo = TransactionRepository(db)

    async def initiate_stk(self, donation_id: uuid.UUID, phone_number: str, amount: float, user_id: Optional[uuid.UUID] = None) -> Dict[str, Any]:
        donation = await self.db.get(Donation, donation_id)
        if not donation:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Donation drive not found")
        ref = f"JMC-{str(uuid.uuid4())[:8].upper()}"
        res = await mpesa_service.initiate_stk_push(
            phone_number=phone_number,
            amount=amount,
            reference=ref,
            description=donation.title[:30],
            shortcode=donation.paybill_number,
            passkey=donation.passkey,
            consumer_key=donation.consumer_key,
            consumer_secret=donation.consumer_secret,
        )
        checkout_id = res.get("CheckoutRequestID", ref)
        tx = Transaction(
            donation_id=donation.id,
            user_id=user_id,
            amount=amount,
            payment_method="M-Pesa",
            account_number=phone_number,
            transaction_reference=checkout_id,
            payment_status="Pending",
        )
        await self.repo.create(tx)
        await self.db.commit()
        return res

    async def verify_cash(self, tx_id: uuid.UUID, admin_id: uuid.UUID) -> Transaction:
        tx = await self.repo.get_by_id(tx_id)
        if not tx:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Transaction not found")
        tx.payment_status = "Completed"
        tx.recorded_by_admin_id = admin_id
        tx.completed_at = datetime.now(timezone.utc).replace(tzinfo=None)
        await self.db.commit()
        return tx

