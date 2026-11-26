import uuid
import logging
from typing import Any, Optional
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import HTTPException, status

from app.models.donations import Donation
from app.models.transactions import Transaction
from app.models.users import User
from app.services.firebase import firebase_service

logger = logging.getLogger(__name__)
MIN_ADMIN_NOTIFICATION_AMOUNT = 10000


def notify_admin_donation_completed(tx: Transaction, donation: Optional[Donation] = None, user: Optional[User] = None) -> None:
    if (tx.amount or 0) < MIN_ADMIN_NOTIFICATION_AMOUNT:
        return
    title_text = donation.title if donation else "a donation drive"
    donor = user.full_name if (user and user.full_name) else (tx.account_name or "A donor")
    body = f"{donor} donated KES {tx.amount:,.0f} to '{title_text}'."
    data = {"type": "admin_donation", "transaction_id": str(tx.id), "amount": str(tx.amount), "donation_id": str(tx.donation_id or "")}
    try:
        firebase_service.send_topic_notification("admins", "💰 New Donation Received", body, data=data)
    except Exception as e:
        logger.error(f"Failed to send admin FCM for tx {tx.id}: {e}")


async def resolve_donation(db: AsyncSession, raw_id: Any) -> Donation:
    if not raw_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Donation ID is required")
    raw_str = str(raw_id).strip()
    is_zakat = raw_str.lower() in ["zakat_al_mal", "zakat", "zakat-al-mal", "zakat_ul_mal"]
    is_general = raw_str.lower() in ["general", "general_donation", "general-donation"]

    if is_zakat:
        res = await db.execute(select(Donation).filter(Donation.title.ilike("%zakat%"), Donation.status == "Active", Donation.is_deleted == False))
        found = res.scalars().first()
        if not found:
            res = await db.execute(select(Donation).filter(Donation.status == "Active", Donation.is_deleted == False))
            found = res.scalars().first()
        if found:
            return found

    if is_general:
        res = await db.execute(select(Donation).filter(Donation.status == "Active", Donation.is_deleted == False))
        found = res.scalars().first()
        if found:
            return found

    try:
        target_id = uuid.UUID(raw_str)
    except ValueError:
        res = await db.execute(select(Donation).filter(Donation.title.ilike(f"%{raw_str}%"), Donation.status == "Active", Donation.is_deleted == False))
        found = res.scalars().first()
        if found:
            return found
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Invalid donation UUID: {raw_id}")

    res = await db.execute(select(Donation).filter(Donation.id == target_id, Donation.is_deleted == False))
    donation = res.scalars().first()
    if not donation:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Donation drive not found")
    return donation
