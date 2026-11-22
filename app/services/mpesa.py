import httpx, base64, logging
from datetime import datetime
from typing import Optional
from app.core.config import settings

logger = logging.getLogger(__name__)

class MpesaService:
    def __init__(self):
        self.consumer_key = settings.MPESA_CONSUMER_KEY
        self.consumer_secret = settings.MPESA_CONSUMER_SECRET
        self.base_url = (settings.MPESA_API_URL or "").rstrip("/")
        self.passkey = settings.MPESA_PASSKEY
        self.shortcode = settings.MPESA_SHORTCODE

    async def get_access_token(self, consumer_key: Optional[str] = None, consumer_secret: Optional[str] = None) -> str:
        ck, cs = consumer_key or self.consumer_key, consumer_secret or self.consumer_secret
        base = self.base_url or "https://api.safaricom.co.ke"
        async with httpx.AsyncClient() as client:
            resp = await client.get(f"{base}/oauth/v1/generate?grant_type=client_credentials", auth=(ck, cs), timeout=15)
            resp.raise_for_status()
            data = resp.json()
            if "access_token" not in data:
                raise ValueError("Failed to obtain M-Pesa token")
            return data["access_token"]

    def _generate_password(self, shortcode: str, passkey: str, timestamp: str) -> str:
        return base64.b64encode(f"{shortcode}{passkey}{timestamp}".encode()).decode()

    async def initiate_stk_push(
        self, phone_number: str, amount: float, reference: str, description: str,
        shortcode: Optional[str] = None, passkey: Optional[str] = None,
        consumer_key: Optional[str] = None, consumer_secret: Optional[str] = None,
    ):
        sc, pk = shortcode or self.shortcode, passkey or self.passkey
        timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
        password = self._generate_password(sc, pk, timestamp)
        token = await self.get_access_token(consumer_key, consumer_secret)
        clean_ref = "".join(c for c in reference if c.isalnum() or c in "-_")[:12] if reference else "JamiaWaqf"
        clean_desc = "".join(c for c in description if c.isalnum() or c in " -_")[:30] if description else "Donation"
        base = self.base_url or "https://api.safaricom.co.ke"

        payload = {
            "BusinessShortCode": sc, "Password": password, "Timestamp": timestamp,
            "TransactionType": "CustomerPayBillOnline", "Amount": max(1, int(round(amount))),
            "PhoneNumber": phone_number, "PartyA": phone_number, "PartyB": sc,
            "CallBackURL": settings.MPESA_CALLBACK_URL, "AccountReference": clean_ref,
            "TransactionDesc": clean_desc,
        }
        async with httpx.AsyncClient() as client:
            resp = await client.post(f"{base}/mpesa/stkpush/v1/processrequest", json=payload, headers={"Authorization": f"Bearer {token}"}, timeout=30)
            resp.raise_for_status()
            return resp.json()

    async def query_stk_status(
        self, checkout_request_id: str, shortcode: Optional[str] = None, passkey: Optional[str] = None,
        consumer_key: Optional[str] = None, consumer_secret: Optional[str] = None,
    ):
        sc, pk = shortcode or self.shortcode, passkey or self.passkey
        timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
        password = self._generate_password(sc, pk, timestamp)
        token = await self.get_access_token(consumer_key, consumer_secret)
        payload = {"BusinessShortCode": sc, "Password": password, "Timestamp": timestamp, "CheckoutRequestID": checkout_request_id}
        async with httpx.AsyncClient() as client:
            resp = await client.post(f"{self.base_url}/mpesa/stkpushquery/v1/query", json=payload, headers={"Authorization": f"Bearer {token}"}, timeout=15)
            resp.raise_for_status()
            return resp.json()

mpesa_service = MpesaService()
