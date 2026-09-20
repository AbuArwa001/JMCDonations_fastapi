from app.core.celery_app import celery_app
from app.db.session import AsyncSessionLocal
from app.workers.auto_close import auto_close_expired_donations

@celery_app.task
def close_expired_donations():
    """Mark donations as closed if their end_date has passed."""
    import asyncio
    
    async def _run():
        async with AsyncSessionLocal() as db:
            closed_count = await auto_close_expired_donations(db)
            print(f"Closed {closed_count} expired donations")
            return closed_count
            
    return asyncio.run(_run())
