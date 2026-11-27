import firebase_admin
from firebase_admin import credentials, auth
from app.core.config import settings
from app.models.users import User
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from fastapi import HTTPException, status
from datetime import datetime, timezone
import json, logging
from app.services.firebase_messaging import (
    send_fcm_notification, send_fcm_topic_notification, send_fcm_multicast
)

logger = logging.getLogger(__name__)

def init_firebase():
    if not firebase_admin._apps and settings.FIREBASE_SERVICE_ACCOUNT_JSON:
        try:
            cert_dict = json.loads(settings.FIREBASE_SERVICE_ACCOUNT_JSON)
            if 'private_key' in cert_dict and '\\n' in cert_dict['private_key']:
                cert_dict['private_key'] = cert_dict['private_key'].replace('\\n', '\n')
            firebase_admin.initialize_app(credentials.Certificate(cert_dict))
        except Exception as e:
            logger.error(f"Firebase init error: {e}")

class FirebaseService:
    def __init__(self):
        init_firebase()

    def verify_token(self, token: str) -> dict:
        try:
            return auth.verify_id_token(token)
        except auth.ExpiredIdTokenError:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Firebase token expired")
        except Exception as e:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=f"Firebase auth failed: {e}")

    async def authenticate_or_sync_firebase_user(self, db: AsyncSession, decoded: dict) -> User:
        uid, email = decoded.get("uid"), decoded.get("email")
        if not uid:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Missing UID")
        user = (await db.execute(select(User).filter(User.firebase_uid == uid))).scalars().first()
        if not user and email:
            user = (await db.execute(select(User).filter(User.email == email))).scalars().first()
            if user:
                user.firebase_uid = uid
        now_utc = datetime.now(timezone.utc).replace(tzinfo=None)
        if not user:
            email = email or f"{uid}@firebase.user"
            username = email.split("@")[0] if "@" in email else f"user_{uid[:8]}"
            user = User(email=email, username=username, full_name=decoded.get("name") or username,
                        firebase_uid=uid, profile_image_url=decoded.get("picture"),
                        is_active=True, is_admin=bool(decoded.get("admin", False)), ss_login=now_utc)
            db.add(user)
        else:
            if not user.firebase_uid:
                user.firebase_uid = uid
            if decoded.get("name") and not user.full_name:
                user.full_name = decoded.get("name")
            user.ss_login = now_utc
        await db.commit()
        await db.refresh(user)
        return user

    def send_notification(self, title: str, body: str, token: str, data: dict = None, image_url: str = None):
        return send_fcm_notification(title, body, token, data, image_url)

    def send_topic_notification(self, topic: str, title: str, body: str, data: dict = None, image_url: str = None):
        return send_fcm_topic_notification(topic, title, body, data, image_url)

    def send_multicast(self, tokens: list, title: str, body: str, data: dict = None, image_url: str = None) -> int:
        return send_fcm_multicast(tokens, title, body, data, image_url)

firebase_service = FirebaseService()
