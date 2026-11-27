import logging
from typing import Optional, Dict, List
from firebase_admin import messaging

logger = logging.getLogger(__name__)

def _get_android_config():
    return messaging.AndroidConfig(
        priority="high",
        notification=messaging.AndroidNotification(
            channel_id="high_importance_channel",
            sound="default",
            priority="high",
            click_action="FLUTTER_NOTIFICATION_CLICK",
        ),
    )

def _get_apns_config():
    return messaging.ApnsConfig(
        payload=messaging.ApnsPayload(
            aps=messaging.Aps(sound="default", content_available=True)
        )
    )

def send_fcm_notification(title: str, body: str, token: str, data: Optional[Dict] = None, image_url: Optional[str] = None):
    try:
        notification = messaging.Notification(title=title, body=body, image=image_url)
        message = messaging.Message(
            notification=notification,
            android=_get_android_config(),
            apns=_get_apns_config(),
            data={str(k): str(v) for k, v in data.items()} if data else None,
            token=token,
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
            android=_get_android_config(),
            apns=_get_apns_config(),
            data={str(k): str(v) for k, v in data.items()} if data else None,
            topic=topic,
        )
        resp = messaging.send(message)
        logger.info(f"Broadcast FCM sent to '{topic}': {resp}")
        return resp
    except Exception as e:
        logger.error(f"Failed to send FCM topic notification to '{topic}': {e}")
        return None

def send_fcm_multicast(tokens: List[str], title: str, body: str, data: Optional[Dict] = None, image_url: Optional[str] = None) -> int:
    if not tokens:
        return 0
    clean_tokens = list({t for t in tokens if t})
    if not clean_tokens:
        return 0
    success = 0
    for i in range(0, len(clean_tokens), 500):
        chunk = clean_tokens[i:i + 500]
        try:
            mm = messaging.MulticastMessage(
                tokens=chunk,
                notification=messaging.Notification(title=title, body=body, image=image_url),
                android=_get_android_config(),
                apns=_get_apns_config(),
                data={str(k): str(v) for k, v in data.items()} if data else None,
            )
            res = messaging.send_each_for_multicast(mm)
            success += res.success_count
        except Exception as e:
            logger.error(f"FCM multicast batch error: {e}")
    return success
