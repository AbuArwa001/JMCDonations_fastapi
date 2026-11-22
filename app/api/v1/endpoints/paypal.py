from typing import Optional
from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel
from app.services.paypal import paypal_service

router = APIRouter()

class CreatePayPalOrderRequest(BaseModel):
    amount: float
    currency: str = "USD"
    return_url: Optional[str] = None
    cancel_url: Optional[str] = None

class CapturePayPalOrderRequest(BaseModel):
    order_id: str

@router.post("/create-order")
async def create_paypal_order(req: CreatePayPalOrderRequest):
    order = await paypal_service.create_order(amount=req.amount, currency=req.currency, return_url=req.return_url, cancel_url=req.cancel_url)
    if not order:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail="Failed to initialize PayPal order")
    return order

@router.post("/capture-order")
async def capture_paypal_order(req: CapturePayPalOrderRequest):
    res = await paypal_service.capture_order(req.order_id)
    if not res:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail="Failed to capture PayPal payment")
    return res

