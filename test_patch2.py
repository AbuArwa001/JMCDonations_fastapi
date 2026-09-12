import sys
sys.path.insert(0, '/root/workspace/JMCDonations_fastapi')
from fastapi.testclient import TestClient
from app.main import app

def test():
    from app.api.v1.deps import get_current_admin_user
    app.dependency_overrides[get_current_admin_user] = lambda: {"id": "test"}
    
    with TestClient(app) as client:
        response = client.patch(
            "/api/v1/donations/4a8dfc39-50eb-494f-b39d-f7b7ebf9c883",
            json={"image_urls": ["https://test.com/image.jpg"]}
        )
        print("Status code:", response.status_code)
        print("Response body:", response.text)

test()
