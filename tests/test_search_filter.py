import pytest
import time
from datetime import datetime, timezone, timedelta
from httpx import AsyncClient, ASGITransport
from app.main import app
from app.core.security import create_access_token
from app.models.users import User
from app.db.session import AsyncSessionLocal

@pytest.fixture
async def async_client():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        yield ac

@pytest.fixture
async def admin_auth():
    async with AsyncSessionLocal() as session:
        unique_suffix = int(time.time() * 1000)
        admin = User(
            email=f"admin_sf_{unique_suffix}@example.com",
            username=f"admin_sf_{unique_suffix}",
            full_name="Admin SF Test",
            is_active=True,
            is_admin=True
        )
        session.add(admin)
        await session.commit()
        await session.refresh(admin)
        token = create_access_token(admin.id)
        return {"Authorization": f"Bearer {token}", "admin": admin}

@pytest.mark.asyncio
async def test_search_and_filter_donations(async_client, admin_auth):
    headers = {"Authorization": admin_auth["Authorization"]}
    unique_str = str(int(time.time() * 1000))

    # 1. Create two categories
    cat1_name = f"Water Waqf {unique_str}"
    cat2_name = f"Education Fund {unique_str}"

    c1_res = await async_client.post(
        "/api/v1/categories/",
        headers=headers,
        json={"category_name": cat1_name, "color": "#00A855"}
    )
    assert c1_res.status_code == 201
    cat1_id = c1_res.json()["id"]

    c2_res = await async_client.post(
        "/api/v1/categories/",
        headers=headers,
        json={"category_name": cat2_name, "color": "#C99335"}
    )
    assert c2_res.status_code == 201
    cat2_id = c2_res.json()["id"]

    # 2. Create donations
    now = datetime.now(timezone.utc)
    d1_payload = {
        "title": f"Borehole Drilling Project {unique_str}",
        "description": "Providing clean water to drought affected areas",
        "target_amount": 50000.0,
        "start_date": now.isoformat(),
        "end_date": (now + timedelta(days=30)).isoformat(),
        "paybill_number": "123456",
        "account_name": "Jamia Mosque",
        "category_id": cat1_id,
        "is_featured": True,
    }
    d2_payload = {
        "title": f"Scholarship Endowment {unique_str}",
        "description": "Funding higher education scholarships for students",
        "target_amount": 100000.0,
        "start_date": now.isoformat(),
        "end_date": (now + timedelta(days=60)).isoformat(),
        "paybill_number": "654321",
        "account_name": "Education Board",
        "category_id": cat2_id,
        "is_featured": False,
    }

    res1 = await async_client.post("/api/v1/donations/", headers=headers, json=d1_payload)
    assert res1.status_code == 201
    res2 = await async_client.post("/api/v1/donations/", headers=headers, json=d2_payload)
    assert res2.status_code == 201

    # Test Search by Title
    s_res = await async_client.get(f"/api/v1/donations/?search=Borehole%20{unique_str}")
    assert s_res.status_code == 200
    s_data = s_res.json()
    assert len(s_data) >= 1
    assert any("Borehole" in d["title"] for d in s_data)

    # Test Search by Category Name keyword
    scat_res = await async_client.get(f"/api/v1/donations/?search=Water%20Waqf%20{unique_str}")
    assert scat_res.status_code == 200
    scat_data = scat_res.json()
    assert len(scat_data) >= 1
    assert any(d["category_name"] == cat1_name for d in scat_data)

    # Test Filter by category__category_name
    f_cat_res = await async_client.get(f"/api/v1/donations/?category__category_name={cat2_name}")
    assert f_cat_res.status_code == 200
    f_cat_data = f_cat_res.json()
    assert len(f_cat_data) >= 1
    assert all(d["category_name"] == cat2_name for d in f_cat_data)

    # Test Ordering by target_amount
    ord_res = await async_client.get(f"/api/v1/donations/?search={unique_str}&ordering=target_amount")
    assert ord_res.status_code == 200
    ord_data = ord_res.json()
    assert len(ord_data) >= 2
    assert ord_data[0]["target_amount"] <= ord_data[1]["target_amount"]
