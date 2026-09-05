from app.core.config import settings
import httpx
import base64
from datetime import datetime
from typing import Optional

class MpesaService:
    def __init__(self):
        self.consumer_key = settings.MPESA_CONSUMER_KEY
        self.consumer_secret = settings.MPESA_CONSUMER_SECRET
        self.base_url = settings.MPESA_API_URL
        self.passkey = settings.MPESA_PASSKEY
        self.shortcode = settings.MPESA_SHORTCODE

    async def get_access_token(self, consumer_key: Optional[str] = None, consumer_secret: Optional[str] = None) -> str:
        ck = consumer_key or self.consumer_key
        cs = consumer_secret or self.consumer_secret
        async with httpx.AsyncClient() as client:
            url = f"{self.base_url}/oauth/v1/generate?grant_type=client_credentials"
            response = await client.get(
                url,
                auth=(ck, cs),
                timeout=15
            )
            data = response.json()
            if "access_token" not in data:
                raise ValueError(f"Failed to get M-Pesa access token: {data}")
            return data["access_token"]

    async def initiate_stk_push(
        self,
        phone_number: str,
        amount: float,
        reference: str,
        description: str,
        shortcode: Optional[str] = None,
        passkey: Optional[str] = None,
        consumer_key: Optional[str] = None,
        consumer_secret: Optional[str] = None,
    ):
        sc = shortcode or self.shortcode
        pk = passkey or self.passkey
        timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
        password = base64.b64encode(
            f"{sc}{pk}{timestamp}".encode()
        ).decode()

        token = await self.get_access_token(consumer_key=consumer_key, consumer_secret=consumer_secret)

        # Sanitize AccountReference: Daraja requires max 12 chars alphanumeric
        clean_ref = "".join(c for c in reference if c.isalnum())[:12] if reference else "JamiaGive"
        clean_desc = "".join(c for c in description if c.isalnum() or c in " -_")[:30] if description else "Donation"

        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.base_url}/mpesa/stkpush/v1/processrequest",
                json={
                    "BusinessShortCode": sc,
                    "Password": password,
                    "Timestamp": timestamp,
                    "TransactionType": "CustomerPayBillOnline",
                    "Amount": max(1, int(round(amount))),
                    "PhoneNumber": phone_number,
                    "PartyA": phone_number,
                    "PartyB": sc,
                    "CallBackURL": settings.MPESA_CALLBACK_URL,
                    "AccountReference": clean_ref,
                    "TransactionDesc": clean_desc,
                },
                headers={
                    "Authorization": f"Bearer {token}",
                },
                timeout=30
            )
            return response.json()

mpesa_service = MpesaService()
