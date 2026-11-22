import pytest

@pytest.mark.asyncio
async def test_root_endpoint(async_client):
    response = await async_client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert "message" in data
    assert "versions" in data

@pytest.mark.asyncio
async def test_v1_health_check(async_client):
    response = await async_client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}

@pytest.mark.asyncio
async def test_v1_router_health(async_client):
    response = await async_client.get("/api/v1/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"

