import logging
from typing import List, Optional, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.models.khutba import DeviceToken, NotificationLog
from app.services.firebase import firebase_service

logger = logging.getLogger(__name__)

async def dispatch_broadcast(
    db: AsyncSession,
    title: str,
    body: str,
    topics: List[str],
    data: Optional[Dict[str, str]] = None,
    image_url: Optional[str] = None,
    notification_type: str = "general",
    related_id_field: Optional[str] = None,
    related_id_val: Optional[Any] = None,
) -> int:
    # 1. Send topic notifications
    for topic in topics:
        try:
            firebase_service.send_topic_notification(
                topic=topic, title=title, body=body, data=data, image_url=image_url
            )
        except Exception as e:
            logger.error(f"Topic error '{topic}': {e}")

    # 2. Multicast to registered devices
    tokens = list((await db.execute(select(DeviceToken.fcm_token))).scalars().all())
    delivered = 0
    if tokens:
        try:
            delivered = firebase_service.send_multicast(
                tokens=tokens, title=title, body=body, data=data, image_url=image_url
            )
        except Exception as e:
            logger.error(f"Multicast error: {e}")

    total_count = max(delivered, len(tokens), 1)

    # 3. Log notification
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
