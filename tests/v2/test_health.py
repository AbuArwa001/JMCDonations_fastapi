import pytest

@pytest.mark.asyncio
async def test_v2_health_envelope(async_client):
    response = await async_client.get("/api/v2/health")
    assert response.status_code == 200
    body = response.json()
    assert body["success"] is True
    assert "data" in body
    assert body["data"]["status"] == "ok"
    assert "meta" in body
    assert body["meta"]["version"] == "v2"

