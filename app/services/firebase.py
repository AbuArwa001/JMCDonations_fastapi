import firebase_admin
from firebase_admin import credentials, auth, messaging
from app.core.config import settings
import json

def init_firebase():
    if not firebase_admin._apps:
        try:
            cert_dict = json.loads(settings.FIREBASE_SERVICE_ACCOUNT_JSON)
            if 'private_key' in cert_dict and '\\n' in cert_dict['private_key']:
                cert_dict['private_key'] = cert_dict['private_key'].replace('\\n', '\n')
            cred = credentials.Certificate(cert_dict)
            firebase_admin.initialize_app(cred)
        except Exception as e:
            print(f"Firebase init error: {e}")

class FirebaseService:
    def __init__(self):
        init_firebase()
        
    def verify_token(self, token: str):
        try:
            decoded_token = auth.verify_id_token(token)
            return decoded_token
        except Exception as e:
            return None

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
