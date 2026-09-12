import asyncio
from fastapi.testclient import TestClient
from app.main import app

def test():
    from app.api.dependencies.auth import get_current_admin_user
    app.dependency_overrides[get_current_admin_user] = lambda: {"id": "test"}
    
    with TestClient(app) as client:
        # Simulate JSON payload from the frontend without images
        response = client.patch(
            "/api/v1/donations/10636fb3-5751-4d32-bc56-d444439c28e9",  # using a real ID if it exists? no, it will 404. Let's just create one or see what crashes. Wait, if it 404s, we don't reach the 500!
            json={
                "title": "",
                "category": "some-uuid",
                "start_date": "",
                "end_date": "",
                "target_amount": 1000,
                "description": "test",
                "paybill_number": "123",
                "account_name": "test",
                "account_number": "",
                "status": "Active"
            }
        )
        print("JSON Status:", response.status_code)
        print("JSON Body:", response.text)

test()
