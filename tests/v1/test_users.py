import pytest

@pytest.mark.asyncio
async def test_users_unauthorized(async_client):
    resp = await async_client.get("/api/v1/users/me")
    assert resp.status_code in [401, 403]

@pytest.mark.asyncio
async def test_admin_list_users(async_client, admin_headers):
    resp = await async_client.get("/api/v1/users", headers=admin_headers)
    assert resp.status_code == 200
    users = resp.json()
    assert isinstance(users, list)
    assert len(users) >= 1

