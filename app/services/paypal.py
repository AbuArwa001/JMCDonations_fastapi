import logging
from typing import Optional, Dict, Any
import httpx
from app.core.config import settings

logger = logging.getLogger(__name__)

class PayPalService:
    def __init__(self):
        self.client_id = settings.PAYPAL_CLIENT_ID
        self.client_secret = settings.PAYPAL_SECRET
        self.base_url = "https://api-m.sandbox.paypal.com" if settings.PAYPAL_MODE == "sandbox" else "https://api-m.paypal.com"

    async def get_access_token(self) -> Optional[str]:
        url = f"{self.base_url}/v1/oauth2/token"
        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                resp = await client.post(url, headers={"Accept": "application/json"}, data={"grant_type": "client_credentials"}, auth=(self.client_id, self.client_secret))
                if resp.status_code == 200:
                    return resp.json().get("access_token")
                logger.error(f"PayPal OAuth failed {resp.status_code}: {resp.text}")
        except Exception as e:
            logger.error(f"Error fetching PayPal token: {e}")
        return None

    async def create_order(self, amount: float, currency: str = "USD", return_url: Optional[str] = None, cancel_url: Optional[str] = None) -> Optional[Dict[str, Any]]:
        token = await self.get_access_token()
        if not token:
            return None
        payload = {
            "intent": "CAPTURE",
            "purchase_units": [{"amount": {"currency_code": currency, "value": f"{amount:.2f}"}}],
            "application_context": {"return_url": return_url, "cancel_url": cancel_url, "user_action": "PAY_NOW"}
        }
        try:
            async with httpx.AsyncClient(timeout=20.0) as client:
                resp = await client.post(f"{self.base_url}/v2/checkout/orders", headers={"Authorization": f"Bearer {token}"}, json=payload)
                if resp.status_code in [200, 201]:
                    return resp.json()
        except Exception as e:
            logger.error(f"PayPal create_order error: {e}")
        return None

    async def capture_order(self, order_id: str) -> Optional[Dict[str, Any]]:
        token = await self.get_access_token()
        if not token:
            return None
        try:
            async with httpx.AsyncClient(timeout=20.0) as client:
                resp = await client.post(f"{self.base_url}/v2/checkout/orders/{order_id}/capture", headers={"Authorization": f"Bearer {token}"})
                if resp.status_code in [200, 201]:
                    return resp.json()
        except Exception as e:
            logger.error(f"PayPal capture error {order_id}: {e}")
        return None

paypal_service = PayPalService()
