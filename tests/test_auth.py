import pytest
from httpx import AsyncClient, ASGITransport
from unittest.mock import patch
from firebase_admin import auth as firebase_auth
from app.main import app

@pytest.fixture
async def async_client():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        yield ac

@pytest.mark.asyncio
async def test_auth_full_flow(async_client):
    import time
    unique_suffix = int(time.time() * 1000)
    user_email = f"testuser_{unique_suffix}@example.com"
    user_name = f"testuser_{unique_suffix}"
    password = "SecurePassword123!"

    # 1. Test Registration
    reg_payload = {
        "email": user_email,
        "username": user_name,
        "full_name": "Test User",
        "password": password,
        "phone_number": "+254700000000"
    }
    reg_resp = await async_client.post("/api/v1/auth/register", json=reg_payload)
    assert reg_resp.status_code == 201
    user_data = reg_resp.json()
    assert user_data["email"] == user_email
    assert user_data["username"] == user_name
    assert "hashed_password" not in user_data
    user_id = user_data["id"]

    # 2. Test Duplicate Registration (Email)
    dup_email_resp = await async_client.post("/api/v1/auth/register", json=reg_payload)
    assert dup_email_resp.status_code == 400
    assert "already registered" in dup_email_resp.json()["detail"].lower()

    # 3. Test Duplicate Registration (Username)
    dup_uname_payload = {
        "email": f"diff_{unique_suffix}@example.com",
        "username": user_name,
        "full_name": "Different User",
        "password": password
    }
    dup_uname_resp = await async_client.post("/api/v1/auth/register", json=dup_uname_payload)
    assert dup_uname_resp.status_code == 400
    assert "already taken" in dup_uname_resp.json()["detail"].lower()

    # 4. Test Normal JSON Login (by email)
    login_resp = await async_client.post("/api/v1/auth/login", json={
        "email": user_email,
        "password": password
    })
    assert login_resp.status_code == 200
    login_data = login_resp.json()
    assert "access_token" in login_data
    assert "refresh_token" in login_data
    assert login_data["token_type"] == "bearer"
    assert login_data["user"]["email"] == user_email
    access_token = login_data["access_token"]
    refresh_token = login_data["refresh_token"]

    # 5. Test Normal JSON Login (by username)
    login_uname_resp = await async_client.post("/api/v1/auth/login", json={
        "username": user_name,
        "password": password
    })
    assert login_uname_resp.status_code == 200

    # 6. Test OAuth2 Password Form Login (/auth/token)
    token_resp = await async_client.post("/api/v1/auth/token", data={
        "username": user_email,
        "password": password
    })
    assert token_resp.status_code == 200
    token_data = token_resp.json()
    assert "access_token" in token_data

    # 7. Test /auth/me with Bearer Token
    me_resp = await async_client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {access_token}"}
    )
    assert me_resp.status_code == 200
    assert me_resp.json()["email"] == user_email
    assert me_resp.json()["id"] == user_id

    # 8. Test /users/me with Bearer Token
    users_me_resp = await async_client.get(
        "/api/v1/users/me",
        headers={"Authorization": f"Bearer {access_token}"}
    )
    assert users_me_resp.status_code == 200
    assert users_me_resp.json()["email"] == user_email

    # 9. Test /auth/me without Token
    unauth_resp = await async_client.get("/api/v1/auth/me")
    assert unauth_resp.status_code == 401

    # 10. Test Refresh Token
    refresh_resp = await async_client.post("/api/v1/auth/refresh", json={
        "refresh_token": refresh_token
    })
    assert refresh_resp.status_code == 200
    new_tokens = refresh_resp.json()
    assert "access_token" in new_tokens
    new_access_token = new_tokens["access_token"]

    # Verify new access token works
    me_new_resp = await async_client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {new_access_token}"}
    )
    assert me_new_resp.status_code == 200

    # 11. Test FCM Token Update
    fcm_resp = await async_client.post(
        "/api/v1/auth/fcm-token",
        headers={"Authorization": f"Bearer {new_access_token}"},
        json={"fcm_token": "fcm_test_token_sample_123"}
    )
    assert fcm_resp.status_code == 200
    assert fcm_resp.json()["status"] == "success"
    assert fcm_resp.json()["fcm_token"] == "fcm_test_token_sample_123"

@pytest.mark.asyncio
async def test_firebase_authentication(async_client):
    import time
    unique_suffix = int(time.time() * 1000)
    fake_fb_uid = f"fb_uid_{unique_suffix}"
    fake_fb_email = f"firebase_user_{unique_suffix}@example.com"
    fake_fb_name = "Firebase Test User"

    mock_decoded_token = {
        "uid": fake_fb_uid,
        "email": fake_fb_email,
        "name": fake_fb_name,
        "picture": "https://example.com/photo.jpg",
        "admin": False
    }

    with patch("firebase_admin.auth.verify_id_token", return_value=mock_decoded_token):
        # 1. Test /api/v1/auth/firebase-login with idToken (Django compatibility)
        fb_login_resp = await async_client.post(
            "/api/v1/auth/firebase-login",
            json={"idToken": "mock_valid_firebase_token"}
        )
        assert fb_login_resp.status_code == 200
        fb_data = fb_login_resp.json()
        assert fb_data["user"]["email"] == fake_fb_email
        assert fb_data["user"]["firebase_uid"] == fake_fb_uid
        assert fb_data["user"]["full_name"] == fake_fb_name
        assert "access_token" in fb_data

        # 2. Test Direct Firebase ID Token in Authorization: Bearer
        # (mirroring JMCDonations FirebaseDRFAuthentication)
        direct_resp = await async_client.get(
            "/api/v1/auth/me",
            headers={"Authorization": "Bearer mock_valid_firebase_token"}
        )
        assert direct_resp.status_code == 200
        assert direct_resp.json()["email"] == fake_fb_email
        assert direct_resp.json()["firebase_uid"] == fake_fb_uid

    # 3. Test Invalid Firebase Token
    with patch("firebase_admin.auth.verify_id_token", side_effect=firebase_auth.InvalidIdTokenError("Invalid token")):
        inv_resp = await async_client.post(
            "/api/v1/auth/firebase-login",
            json={"id_token": "mock_invalid_token"}
        )
        assert inv_resp.status_code == 401
        assert "invalid" in inv_resp.json()["detail"].lower()

    # 4. Test Expired Firebase Token
    with patch("firebase_admin.auth.verify_id_token", side_effect=firebase_auth.ExpiredIdTokenError("Expired", None)):
        exp_resp = await async_client.post(
            "/api/v1/auth/firebase-login",
            json={"id_token": "mock_expired_token"}
        )
        assert exp_resp.status_code == 401
        assert "expired" in exp_resp.json()["detail"].lower()
