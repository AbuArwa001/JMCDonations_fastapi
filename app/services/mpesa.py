from app.core.config import settings
import httpx
import base64
from datetime import datetime

class MpesaService:
    def __init__(self):
        self.consumer_key = settings.MPESA_CONSUMER_KEY
        self.consumer_secret = settings.MPESA_CONSUMER_SECRET
        self.base_url = settings.MPESA_API_URL
        self.passkey = settings.MPESA_PASSKEY
        self.shortcode = settings.MPESA_SHORTCODE

    async def get_access_token(self):
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{self.base_url}/mpesa/access-token/v1/token",
                auth=(self.consumer_key, self.consumer_secret),
                timeout=10
            )
            return response.json()["access_token"]

    async def initiate_stk_push(self, phone_number: str, amount: float, reference: str, description: str):
        timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
        password = base64.b64encode(
            f"{self.shortcode}{self.passkey}{timestamp}".encode()
        ).decode()

        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.base_url}/mpesa/stkpush/v1/processrequest",
                json={
                    "BusinessShortCode": self.shortcode,
                    "Password": password,
                    "Timestamp": timestamp,
                    "TransactionType": "CustomerPayBillOnline",
                    "Amount": amount,
                    "PhoneNumber": phone_number,
                    "PartyA": phone_number,
                    "PartyB": self.shortcode,
                    "CallBackURL": settings.MPESA_CALLBACK_URL,
                    "AccountReference": reference,
                    "TransactionDesc": description,
                },
                headers={
                    "Authorization": f"Bearer {await self.get_access_token()}",
                },
                timeout=30
            )
            return response.json()

mpesa_service = MpesaService()
