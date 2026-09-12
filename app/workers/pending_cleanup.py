"""
Background worker: auto-expire pending transactions older than 1 hour.
Runs every 30 minutes via asyncio loop, registered in app lifespan.
"""
import asyncio
import logging
from datetime import datetime, timezone, timedelta

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import AsyncSessionLocal as async_session_factory

logger = logging.getLogger(__name__)

PENDING_EXPIRY_HOURS = 1
CHECK_INTERVAL_SECONDS = 30 * 60  # run every 30 minutes


async def expire_stale_pending_transactions() -> None:
    """Mark any Pending transactions older than PENDING_EXPIRY_HOURS as Failed."""
    from app.models.transactions import Transaction  # local import to avoid circular

    cutoff = datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(hours=PENDING_EXPIRY_HOURS)

    async with async_session_factory() as db:
        try:
            result = await db.execute(
                select(Transaction).filter(
                    Transaction.payment_status == "Pending",
                    Transaction.donated_at <= cutoff,
                )
            )
            stale_txs = result.scalars().all()

            if stale_txs:
                for tx in stale_txs:
                    tx.payment_status = "Failed"
                    logger.info(
                        f"[PendingCleanup] Transaction {tx.id} expired "
                        f"(created {tx.donated_at}, cutoff {cutoff})"
                    )
                await db.commit()
                logger.info(f"[PendingCleanup] Expired {len(stale_txs)} stale pending transaction(s).")
            else:
                logger.debug("[PendingCleanup] No stale pending transactions found.")
        except Exception as e:
            logger.error(f"[PendingCleanup] Error during cleanup: {e}")
            await db.rollback()


async def pending_cleanup_loop() -> None:
    """Runs forever, calling expire_stale_pending_transactions every CHECK_INTERVAL_SECONDS."""
    logger.info("[PendingCleanup] Worker started.")
    while True:
        await expire_stale_pending_transactions()
        await asyncio.sleep(CHECK_INTERVAL_SECONDS)
