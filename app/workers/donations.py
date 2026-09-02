from app.core.celery_app import celery_app
from app.db.session import SessionLocal
from datetime import datetime
from app.models.donations import Donation

@celery_app.task
def close_expired_donations():
    """Mark donations as closed if their end_date has passed."""
    import asyncio
    
    async def _run():
        async with SessionLocal() as db:
            now = datetime.utcnow()
            print(f"Closing expired donations as of {now}")
            # Stub implementation
            
    asyncio.run(_run())
    return "Donations checked"
