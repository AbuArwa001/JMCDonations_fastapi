import pytest

@pytest.mark.asyncio
async def test_v2_analytics_summary(async_client, admin_headers):
    response = await async_client.get("/api/v2/analytics/summary", headers=admin_headers)
    assert response.status_code == 200
    body = response.json()
    assert body["success"] is True
    assert "data" in body
    assert "total_revenue" in body["data"]
    assert "conversion_rate" in body["data"]

