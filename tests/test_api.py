import pytest
from httpx import AsyncClient, ASGITransport
from app.main import app

@pytest.fixture
async def async_client():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        yield ac

@pytest.mark.asyncio
async def test_health_check(async_client):
    response = await async_client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}

@pytest.mark.asyncio
async def test_read_root(async_client):
    response = await async_client.get("/")
    assert response.status_code == 200
    assert "message" in response.json()

@pytest.mark.asyncio
async def test_openapi_docs(async_client):
    response = await async_client.get("/api/v1/openapi.json")
    assert response.status_code == 200
    assert "info" in response.json()

@pytest.mark.asyncio
async def test_users_unauthorized_access(async_client):
    # Attempting to fetch current user without auth token should fail
    response = await async_client.get("/api/v1/users/me")
    assert response.status_code in [401, 403]

@pytest.mark.asyncio
async def test_zakat_nisab_rate(async_client):
    # The endpoint could return 404 if not set, or 200 if set
    response = await async_client.get("/api/v1/zakat/nisab")
    assert response.status_code in [200, 404]

@pytest.mark.asyncio
async def test_auth_login_invalid_credentials(async_client):
    # Testing authentication with invalid credentials
    data = {"username": "invalid@example.com", "password": "wrongpassword"}
    response = await async_client.post("/api/v1/auth/login", data=data)
    assert response.status_code in [400, 401]
