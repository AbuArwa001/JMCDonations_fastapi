from celery import Celery
from app.core.config import settings

celery_app = Celery(
    "jmcdonations_worker",
    broker=settings.CELERY_BROKER_URL,
    backend=settings.CELERY_RESULT_BACKEND,
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="Africa/Nairobi",
    enable_utc=True,
    # Periodic tasks setup (beat)
    beat_schedule={
        "cleanup-expired-transactions-hourly": {
            "task": "app.workers.transactions.cleanup_expired_transactions",
            "schedule": 3600.0, # Every hour
        },
        "close-expired-donations-hourly": {
            "task": "app.workers.donations.close_expired_donations",
            "schedule": 3600.0,
        },
    }
)
