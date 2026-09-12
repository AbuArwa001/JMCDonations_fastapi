import asyncio
from fastapi.testclient import TestClient
from app.main import app

def test():
    from app.api.dependencies.auth import get_current_admin_user
    app.dependency_overrides[get_current_admin_user] = lambda: {"id": "test"}
    
    with TestClient(app) as client:
        # Simulate form data upload
        response = client.patch(
            "/api/v1/donations/00000000-0000-0000-0000-000000000000",
            data={"title": "Test"},
            files={"uploaded_images": ("test.jpg", b"abc", "image/jpeg")}
        )
        print("FormData Status:", response.status_code)
        print("FormData Body:", response.text)

test()
