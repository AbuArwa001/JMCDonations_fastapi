"""
Background worker: auto-close donation drives whose end_date has passed.
Runs periodically via asyncio loop, registered in app lifespan.
"""
import asyncio
import logging
from datetime import datetime, timezone

from sqlalchemy import update, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import AsyncSessionLocal as async_session_factory
from app.models.donations import Donation

logger = logging.getLogger(__name__)

CHECK_INTERVAL_SECONDS = 5 * 60  # run every 5 minutes


async def auto_close_expired_donations(db: AsyncSession) -> int:
    """
    Find all active donation drives whose end_date is in the past,
    and update their status to 'Closed'.
    Returns the number of drives closed.
    """
    now = datetime.now(timezone.utc).replace(tzinfo=None)
    try:
        stmt = (
            update(Donation)
            .where(
                Donation.status == "Active",
                Donation.end_date < now,
                Donation.is_deleted == False,
            )
            .values(
                status="Closed",
                updated_at=now,
            )
        )
        result = await db.execute(stmt)
        count = result.rowcount
        if count > 0:
            await db.commit()
            logger.info(f"[AutoCloseDonations] Auto-closed {count} expired donation drive(s).")
        return count
    except Exception as e:
        logger.error(f"[AutoCloseDonations] Error auto-closing donations: {e}")
        await db.rollback()
        return 0


async def expired_donations_loop() -> None:
    """
    Runs forever, calling auto_close_expired_donations every CHECK_INTERVAL_SECONDS.
    """
    logger.info("[AutoCloseDonations] Worker started.")
    while True:
        try:
            async with async_session_factory() as db:
                await auto_close_expired_donations(db)
        except Exception as e:
            logger.error(f"[AutoCloseDonations] Loop execution error: {e}")
        await asyncio.sleep(CHECK_INTERVAL_SECONDS)
