import pytest

@pytest.mark.asyncio
async def test_v2_users_profile_envelope(async_client, admin_headers):
    response = await async_client.get("/api/v2/users/me", headers=admin_headers)
    assert response.status_code == 200
    body = response.json()
    assert body["success"] is True
    assert "data" in body
    assert body["data"]["is_admin"] is True
    assert "role" in body["data"]
    assert "meta" in body
    assert body["meta"]["version"] == "v2"

