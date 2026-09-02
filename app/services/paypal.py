from app.core.config import settings
import httpx

class PayPalService:
    def __init__(self):
        self.client_id = settings.PAYPAL_CLIENT_ID
        self.client_secret = settings.PAYPAL_SECRET
        self.mode = settings.PAYPAL_MODE
        self.base_url = "https://api-m.sandbox.paypal.com" if self.mode == "sandbox" else "https://api-m.paypal.com"

    async def get_access_token(self):
        # Implementation for OAuth token
        pass

    async def create_order(self, amount: float, currency: str = "USD"):
        # Implementation for Order Creation
        pass

paypal_service = PayPalService()
