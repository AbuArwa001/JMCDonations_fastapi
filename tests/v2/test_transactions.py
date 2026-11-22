import pytest

@pytest.mark.asyncio
async def test_v2_transactions_list(async_client, admin_headers):
    response = await async_client.get("/api/v2/transactions?page=1&page_size=10", headers=admin_headers)
    assert response.status_code == 200
    body = response.json()
    assert body["success"] is True
    assert "items" in body
    assert "pagination" in body
    assert body["pagination"]["page"] == 1

