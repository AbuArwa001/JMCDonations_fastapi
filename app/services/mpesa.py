from app.core.config import settings
import httpx
import base64
import logging
from datetime import datetime
from typing import Optional

logger = logging.getLogger(__name__)

class MpesaService:
    def __init__(self):
        self.consumer_key = settings.MPESA_CONSUMER_KEY
        self.consumer_secret = settings.MPESA_CONSUMER_SECRET
        self.base_url = (settings.MPESA_API_URL or "").rstrip("/")
        self.passkey = settings.MPESA_PASSKEY
        self.shortcode = settings.MPESA_SHORTCODE

    async def get_access_token(self, consumer_key: Optional[str] = None, consumer_secret: Optional[str] = None) -> str:
        ck = consumer_key or self.consumer_key
        cs = consumer_secret or self.consumer_secret
        base = self.base_url or "https://api.safaricom.co.ke"
        async with httpx.AsyncClient() as client:
            url = f"{base}/oauth/v1/generate?grant_type=client_credentials"
            try:
                response = await client.get(
                    url,
                    auth=(ck, cs),
                    timeout=15
                )
                response.raise_for_status()
                data = response.json()
            except httpx.HTTPStatusError as e:
                err_text = e.response.text
                logger.error(f"Safaricom OAuth HTTPStatusError {e.response.status_code}: {err_text}")
                raise ValueError(f"M-Pesa Authentication Failed ({e.response.status_code}): {err_text}")
            except httpx.HTTPError as e:
                logger.error(f"Safaricom OAuth HTTPError: {e}")
                raise ValueError("Connection failed (Network Error). Please check internet connection.")
            except ValueError:
                raise ValueError("Service temporarily unavailable (Invalid Response).")

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

        # Sanitize AccountReference: Daraja requires max 12 chars alphanumeric without spaces
        clean_ref = "".join(c for c in reference if c.isalnum() or c in "-_")[:12].strip() if reference else "JamiaWaqf"
        clean_desc = "".join(c for c in description if c.isalnum() or c in " -_")[:30].strip() if description else "Donation"
        base = self.base_url or "https://api.safaricom.co.ke"

        async with httpx.AsyncClient() as client:
            try:
                response = await client.post(
                    f"{base}/mpesa/stkpush/v1/processrequest",
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
                response.raise_for_status()
                return response.json()
            except httpx.HTTPStatusError as e:
                err_text = e.response.text
                logger.error(f"Safaricom STK Push failed status {e.response.status_code}: {err_text}")
                try:
                    err_json = e.response.json()
                    msg = err_json.get("errorMessage") or err_json.get("ResponseDescription") or err_text
                except Exception:
                    msg = err_text
                raise ValueError(f"Safaricom error: {msg}")
            except httpx.HTTPError as e:
                logger.error(f"Safaricom STK Push network error: {e}")
                raise ValueError("Service temporarily unavailable (Network Error). Please try again.")
            except ValueError:
                raise ValueError("Service temporarily unavailable (Bad Gateway). Please try again.")

    async def query_stk_status(
        self,
        checkout_request_id: str,
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

        async with httpx.AsyncClient() as client:
            try:
                response = await client.post(
                    f"{self.base_url}/mpesa/stkpushquery/v1/query",
                    json={
                        "BusinessShortCode": sc,
                        "Password": password,
                        "Timestamp": timestamp,
                        "CheckoutRequestID": checkout_request_id,
                    },
                    headers={
                        "Authorization": f"Bearer {token}",
                    },
                    timeout=15
                )
                response.raise_for_status()
                return response.json()
            except httpx.HTTPError:
                raise ValueError("Service temporarily unavailable (Network Error).")
            except ValueError:
                raise ValueError("Service temporarily unavailable (Bad Gateway).")

mpesa_service = MpesaService()
