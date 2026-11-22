import logging
from typing import Optional, Dict
from firebase_admin import messaging

logger = logging.getLogger(__name__)

def send_fcm_notification(title: str, body: str, token: str, data: Optional[Dict] = None, image_url: Optional[str] = None):
    try:
        notification = messaging.Notification(title=title, body=body, image=image_url)
        message = messaging.Message(
            notification=notification,
            data={str(k): str(v) for k, v in data.items()} if data else None,
            token=token
        )
        return messaging.send(message)
    except Exception as e:
        logger.error(f"Failed to send direct FCM notification: {e}")
        return None

def send_fcm_topic_notification(topic: str, title: str, body: str, data: Optional[Dict] = None, image_url: Optional[str] = None):
    try:
        notification = messaging.Notification(title=title, body=body, image=image_url)
        message = messaging.Message(
            notification=notification,
            data={str(k): str(v) for k, v in data.items()} if data else None,
            topic=topic
        )
        resp = messaging.send(message)
        logger.info(f"Broadcast FCM sent to '{topic}': {resp}")
        return resp
    except Exception as e:
        logger.error(f"Failed to send FCM topic notification to '{topic}': {e}")
        return None

