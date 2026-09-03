import firebase_admin
from firebase_admin import credentials, auth, messaging
from app.core.config import settings
from app.models.users import User
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from fastapi import HTTPException, status
from datetime import datetime, timezone
import json
import logging

logger = logging.getLogger(__name__)

def init_firebase():
    if not firebase_admin._apps:
        try:
            if settings.FIREBASE_SERVICE_ACCOUNT_JSON:
                cert_dict = json.loads(settings.FIREBASE_SERVICE_ACCOUNT_JSON)
                if 'private_key' in cert_dict and '\\n' in cert_dict['private_key']:
                    cert_dict['private_key'] = cert_dict['private_key'].replace('\\n', '\n')
                cred = credentials.Certificate(cert_dict)
                firebase_admin.initialize_app(cred)
                logger.info("Firebase initialized successfully")
        except Exception as e:
            logger.error(f"Firebase init error: {e}")

class FirebaseService:
    def __init__(self):
        init_firebase()
        
    def verify_token(self, token: str) -> dict:
        """
        Verify a Firebase ID token.
        Raises HTTPException on error.
        """
        try:
            decoded_token = auth.verify_id_token(token)
            return decoded_token
        except auth.ExpiredIdTokenError:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Firebase token expired",
                headers={"WWW-Authenticate": "Bearer"},
            )
        except auth.InvalidIdTokenError:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid Firebase token",
                headers={"WWW-Authenticate": "Bearer"},
            )
        except Exception as e:
            logger.error(f"Firebase auth verification error: {e}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=f"Firebase authentication failed: {str(e)}",
                headers={"WWW-Authenticate": "Bearer"},
            )

    async def authenticate_or_sync_firebase_user(self, db: AsyncSession, decoded_token: dict) -> User:
        """
        Find or create a local User record from verified Firebase token claims.
        Matches behavior from JMCDonations Django authentication backend.
        """
        uid = decoded_token.get("uid")
        email = decoded_token.get("email")
        full_name = decoded_token.get("name") or ""
        picture = decoded_token.get("picture")
        is_firebase_admin = bool(decoded_token.get("admin", False))

        if not uid:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Firebase token missing UID"
            )

        # 1. Lookup by firebase_uid first
        result = await db.execute(select(User).filter(User.firebase_uid == uid))
        user = result.scalars().first()

        # 2. If not found, lookup by email
        if not user and email:
            result = await db.execute(select(User).filter(User.email == email))
            user = result.scalars().first()
            if user:
                user.firebase_uid = uid

        now_utc = datetime.now(timezone.utc).replace(tzinfo=None)

        # 3. If still not found, create new user
        if not user:
            if not email:
                email = f"{uid}@firebase.user"
                
            base_username = email.split("@")[0] if "@" in email else f"user_{uid[:8]}"
            username = base_username

            # Ensure unique username
            counter = 1
            while True:
                existing = await db.execute(select(User).filter(User.username == username))
                if not existing.scalars().first():
                    break
                username = f"{base_username}_{counter}"
                counter += 1

            user = User(
                email=email,
                username=username,
                full_name=full_name or username,
                firebase_uid=uid,
                profile_image_url=picture,
                is_active=True,
                is_admin=is_firebase_admin,
                ss_login=now_utc
            )
            db.add(user)
        else:
            # Sync existing user details
            if not user.firebase_uid:
                user.firebase_uid = uid
            if is_firebase_admin and not user.is_admin:
                user.is_admin = True
            if full_name and not user.full_name:
                user.full_name = full_name
            if picture and not user.profile_image_url:
                user.profile_image_url = picture
            user.ss_login = now_utc

        await db.commit()
        await db.refresh(user)
        return user

    def send_notification(self, title: str, body: str, token: str):
        message = messaging.Message(
            notification=messaging.Notification(
                title=title,
                body=body
            ),
            token=token
        )
        response = messaging.send(message)
        return response

firebase_service = FirebaseService()
