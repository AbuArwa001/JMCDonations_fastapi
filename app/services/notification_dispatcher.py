import logging
from typing import Optional, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from app.models.khutba import DeviceToken, NotificationLog
from app.services.firebase import firebase_service

logger = logging.getLogger(__name__)

async def dispatch_broadcast(
    db: AsyncSession,
    title: str,
    body: str,
    topic: str,
    data: Optional[Dict[str, str]] = None,
    image_url: Optional[str] = None,
    notification_type: str = "general",
    related_id_field: Optional[str] = None,
    related_id_val: Optional[Any] = None,
) -> int:
    tag = f"{notification_type}_{related_id_val}" if related_id_val else notification_type

    # 1. Broadcast once to the designated topic
    try:
        firebase_service.send_topic_notification(
            topic=topic,
            title=title,
            body=body,
            data=data,
            image_url=image_url,
            tag=tag,
        )
    except Exception as e:
        logger.error(f"FCM topic error for '{topic}': {e}")

    # 2. Get registered device count for UI metrics
    device_count = (await db.execute(select(func.count(DeviceToken.id)))).scalar_one() or 0
    total_count = max(device_count, 1)

    # 3. Log notification in database
    log_kwargs: Dict[str, Any] = {
        "title": title,
        "body": body,
        "image_url": image_url,
        "notification_type": notification_type,
        "recipient_count": total_count,
    }
    if related_id_field and related_id_val is not None:
        log_kwargs[related_id_field] = related_id_val

    try:
        log = NotificationLog(**log_kwargs)
        db.add(log)
        await db.commit()
    except Exception as e:
        logger.error(f"Log save error: {e}")

    return total_count
