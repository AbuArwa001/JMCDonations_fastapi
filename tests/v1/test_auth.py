import pytest

@pytest.mark.asyncio
async def test_register_and_login_flow(async_client):
    payload = {
        "email": "donor@example.com",
        "username": "donor123",
        "full_name": "Generous Donor",
        "phone_number": "+254712345678",
        "password": "StrongPassword123!"
    }
    reg_resp = await async_client.post("/api/v1/auth/register", json=payload)
    assert reg_resp.status_code == 201
    reg_data = reg_resp.json()
    assert "access_token" in reg_data
    assert reg_data["user"]["email"] == "donor@example.com"

    login_resp = await async_client.post("/api/v1/auth/login", json={
        "email": "donor@example.com",
        "password": "StrongPassword123!"
    })
    assert login_resp.status_code == 200
    assert "access_token" in login_resp.json()

@pytest.mark.asyncio
async def test_login_invalid_credentials(async_client):
    resp = await async_client.post("/api/v1/auth/login", json={
        "email": "nonexistent@example.com",
        "password": "wrong"
    })
    assert resp.status_code == 401

