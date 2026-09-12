import asyncio
from fastapi.testclient import TestClient
from app.main import app

def test():
    from app.api.dependencies.auth import get_current_admin_user
    app.dependency_overrides[get_current_admin_user] = lambda: {"id": "test"}
    
    with TestClient(app) as client:
        # Create a real drive first
        create_res = client.post("/api/v1/donations/", json={"title": "Test Drive"})
        drive_id = create_res.json()["id"]
        
        # Now update it with some valid fields but empty title
        response = client.patch(
            f"/api/v1/donations/{drive_id}",
            json={
                "title": "",
            }
        )
        print("JSON Status:", response.status_code)
        print("JSON Body:", response.text)
test()
