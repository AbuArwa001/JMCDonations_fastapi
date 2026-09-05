import pytest
from httpx import AsyncClient, ASGITransport
from app.main import app

@pytest.mark.asyncio
async def test_user_stats_and_avatar():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        # 1. Login as Khalfan
        res = await ac.post("/api/v1/auth/login", json={
            "email_or_username": "khalfanathman12@gmail.com",
            "password": "Khalif01#321"
        })
        assert res.status_code == 200, res.text
        data = res.json()
        token = data["access_token"]
        user = data["user"]

        # Ensure total_donations and total_impact are populated and > 0
        assert user["total_donations"] >= 1
        assert user["total_impact"] >= 150000.0
        assert user["profile_image_url"] is not None
        assert not user["profile_image_url"].endswith(".svg")

        # 2. Fetch /users/me
        res_me = await ac.get("/api/v1/users/me", headers={"Authorization": f"Bearer {token}"})
        assert res_me.status_code == 200, res_me.text
        user_me = res_me.json()
        assert user_me["total_donations"] >= 1
        assert user_me["total_impact"] >= 150000.0

        # 3. Upload avatar
        dummy_png = b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x06\x00\x00\x00\x1f\x15c4\x00\x00\x00\nIDATx\x9cc\x00\x01\x00\x00\x05\x00\x01\r\n-\xb4\x00\x00\x00\x00IEND\xaeB`\x82"
        files = {"file": ("avatar.png", dummy_png, "image/png")}
        res_avatar = await ac.post(
            "/api/v1/users/me/avatar",
            headers={"Authorization": f"Bearer {token}"},
            files=files
        )
        assert res_avatar.status_code == 200, res_avatar.text
        assert "/static/avatars/" in res_avatar.json()["profile_image_url"]
