import pytest
from datetime import datetime, timezone, timedelta

@pytest.mark.asyncio
async def test_list_donations_empty(async_client):
    response = await async_client.get("/api/v1/donations")
    assert response.status_code == 200
    assert isinstance(response.json(), list)

@pytest.mark.asyncio
async def test_create_donation_drive(async_client, admin_headers):
    # 1. Create Category first
    cat_resp = await async_client.post("/api/v1/categories", json={"category_name": "Medical Support", "color": "#10b981"}, headers=admin_headers)
    assert cat_resp.status_code == 201
    cat_id = cat_resp.json()["id"]

    now = datetime.now(timezone.utc)
    drive_data = {
        "title": "Emergency Hospital Relief",
        "description": "Funding emergency healthcare treatment for families in need",
        "target_amount": 500000.0,
        "start_date": now.isoformat(),
        "end_date": (now + timedelta(days=30)).isoformat(),
        "paybill_number": "150770",
        "account_name": "JamiaMedical",
        "category_id": cat_id,
        "image_urls": []
    }
    resp = await async_client.post("/api/v1/donations", json=drive_data, headers=admin_headers)
    assert resp.status_code == 201
    res_json = resp.json()
    assert res_json["title"] == "Emergency Hospital Relief"
    assert res_json["collected_amount"] == 0.0

