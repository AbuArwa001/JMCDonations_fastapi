import logging
from typing import Dict, Any
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession
from app.api.deps import get_db, get_optional_current_user
from app.services.transaction_service import TransactionService
from app.services.mpesa import mpesa_service
from app.schemas.v1.transactions import STKPushRequest
from app.models.transactions import Transaction

logger = logging.getLogger(__name__)
router = APIRouter()

@router.post("/stkpush")
async def initiate_stk_push(req: STKPushRequest, current_user=Depends(get_optional_current_user), db: AsyncSession = Depends(get_db)):
    uid = current_user.id if current_user else None
    return await TransactionService(db).initiate_stk(donation_id=req.donation_id, phone_number=req.phone_number, amount=req.amount, user_id=uid)

@router.post("/callback")
@router.post("/callback/")
async def mpesa_callback(request: Request, db: AsyncSession = Depends(get_db)):
    payload = await request.json()
    logger.info(f"M-Pesa callback received: {payload}")
    cb = payload.get("Body", {}).get("stkCallback", {})
    checkout_id = cb.get("CheckoutRequestID")
    result_code = cb.get("ResultCode")
    if checkout_id:
        tx = await TransactionService(db).repo.get_by_reference(checkout_id)
        if tx:
            if str(result_code) == "0":
                tx.payment_status = "Completed"
                tx.completed_at = datetime.now(timezone.utc).replace(tzinfo=None)
                items = cb.get("CallbackMetadata", {}).get("Item", [])
                for item in items:
                    if item.get("Name") == "MpesaReceiptNumber":
                        tx.mpesa_receipt = item.get("Value")
            else:
                tx.payment_status = "Failed"
            await db.commit()
    return {"ResultCode": 0, "ResultDesc": "Success"}

