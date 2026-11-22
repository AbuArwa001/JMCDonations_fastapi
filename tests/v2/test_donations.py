import pytest

@pytest.mark.asyncio
async def test_v2_donations_pagination(async_client):
    response = await async_client.get("/api/v2/donations?page=1&page_size=10")
    assert response.status_code == 200
    body = response.json()
    assert body["success"] is True
    assert "items" in body
    assert "pagination" in body
    assert body["pagination"]["page"] == 1
    assert body["pagination"]["page_size"] == 10

