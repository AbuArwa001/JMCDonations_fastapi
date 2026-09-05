import logging
from typing import Optional, Dict, Any
import httpx
from app.core.config import settings

logger = logging.getLogger(__name__)

class PayPalService:
    def __init__(self):
        self.client_id = settings.PAYPAL_CLIENT_ID
        self.client_secret = settings.PAYPAL_SECRET
        self.mode = settings.PAYPAL_MODE
        self.base_url = (
            "https://api-m.sandbox.paypal.com"
            if self.mode == "sandbox"
            else "https://api-m.paypal.com"
        )

    async def get_access_token(self) -> Optional[str]:
        url = f"{self.base_url}/v1/oauth2/token"
        headers = {
            "Accept": "application/json",
            "Accept-Language": "en_US",
        }
        data = {"grant_type": "client_credentials"}

        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                response = await client.post(
                    url,
                    headers=headers,
                    data=data,
                    auth=(self.client_id, self.client_secret),
                )
                if response.status_code == 200:
                    return response.json().get("access_token")
                else:
                    logger.error(f"PayPal OAuth failed: {response.status_code} - {response.text}")
                    return None
        except Exception as e:
            logger.error(f"Error fetching PayPal access token: {e}")
            return None

    async def create_order(
        self,
        amount: float,
        currency: str = "USD",
        return_url: Optional[str] = None,
        cancel_url: Optional[str] = None,
    ) -> Optional[Dict[str, Any]]:
        access_token = await self.get_access_token()
        if not access_token:
            logger.error("Cannot create PayPal order: access token is None")
            return None

        url = f"{self.base_url}/v2/checkout/orders"
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {access_token}",
        }
        payload = {
            "intent": "CAPTURE",
            "purchase_units": [
                {
                    "amount": {
                        "currency_code": currency,
                        "value": f"{amount:.2f}",
                    }
                }
            ],
            "application_context": {
                "return_url": return_url,
                "cancel_url": cancel_url,
                "user_action": "PAY_NOW",
            },
        }

        try:
            async with httpx.AsyncClient(timeout=20.0) as client:
                response = await client.post(url, headers=headers, json=payload)
                if response.status_code in [200, 201]:
                    return response.json()
                else:
                    logger.error(f"PayPal create_order failed: {response.status_code} - {response.text}")
                    return None
        except Exception as e:
            logger.error(f"Error creating PayPal order: {e}")
            return None

    async def capture_order(self, order_id: str) -> Optional[Dict[str, Any]]:
        access_token = await self.get_access_token()
        if not access_token:
            logger.error("Cannot capture PayPal order: access token is None")
            return None

        url = f"{self.base_url}/v2/checkout/orders/{order_id}/capture"
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {access_token}",
        }

        try:
            async with httpx.AsyncClient(timeout=20.0) as client:
                response = await client.post(url, headers=headers)
                if response.status_code in [200, 201]:
                    return response.json()
                else:
                    logger.error(f"PayPal capture_order failed: {response.status_code} - {response.text}")
                    return None
        except Exception as e:
            logger.error(f"Error capturing PayPal order {order_id}: {e}")
            return None

paypal_service = PayPalService()
