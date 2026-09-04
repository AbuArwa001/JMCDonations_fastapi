import pytest
import uuid
import time
from datetime import datetime, date, time as dtime, timezone, timedelta
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
        # Create or fetch an admin user
        unique_suffix = int(time.time() * 1000)
        admin = User(
            email=f"admin_{unique_suffix}@example.com",
            username=f"admin_{unique_suffix}",
            full_name="Admin Test",
            is_active=True,
            is_admin=True
        )
        session.add(admin)
        await session.commit()
        await session.refresh(admin)
        token = create_access_token(admin.id)
        return {"Authorization": f"Bearer {token}", "admin": admin}

@pytest.fixture
async def user_auth():
    async with AsyncSessionLocal() as session:
        unique_suffix = int(time.time() * 1000)
        user = User(
            email=f"user_{unique_suffix}@example.com",
            username=f"user_{unique_suffix}",
            full_name="Regular Test User",
            is_active=True,
            is_admin=False
        )
        session.add(user)
        await session.commit()
        await session.refresh(user)
        token = create_access_token(user.id)
        return {"Authorization": f"Bearer {token}", "user": user}


@pytest.mark.asyncio
async def test_donations_crud_and_soft_delete(async_client, admin_auth, user_auth):
    headers = {"Authorization": admin_auth["Authorization"]}
    user_headers = {"Authorization": user_auth["Authorization"]}

    # 1. Create a Category for the donation
    cat_resp = await async_client.post(
        "/api/v1/categories/",
        headers=headers,
        json={"category_name": "Emergency Relief", "color": "#E53E3E"}
    )
    assert cat_resp.status_code == 201
    category_id = cat_resp.json()["id"]

    # 2. Create a Donation
    donation_data = {
        "title": "Gaza Medical Aid Drive",
        "description": "Urgent hospital supplies and medicine",
        "target_amount": 500000.0,
        "start_date": datetime.now(timezone.utc).isoformat(),
        "end_date": (datetime.now(timezone.utc) + timedelta(days=30)).isoformat(),
        "paybill_number": "150770",
        "account_name": "Jamia Relief",
        "account_number": "MED-001",
        "category_id": category_id,
        "is_featured": True
    }
    create_resp = await async_client.post(
        "/api/v1/donations/",
        headers=headers,
        json=donation_data
    )
    assert create_resp.status_code == 201
    donation = create_resp.json()
    donation_id = donation["id"]
    assert donation["title"] == "Gaza Medical Aid Drive"
    assert donation["is_deleted"] is False

    # 3. Read Donation Details
    detail_resp = await async_client.get(f"/api/v1/donations/{donation_id}")
    assert detail_resp.status_code == 200
    assert detail_resp.json()["id"] == donation_id

    # 4. Update Donation
    update_resp = await async_client.patch(
        f"/api/v1/donations/{donation_id}",
        headers=headers,
        json={"description": "Updated relief description"}
    )
    assert update_resp.status_code == 200
    assert update_resp.json()["description"] == "Updated relief description"

    # 5. User Save & Unsave
    save_resp = await async_client.post(f"/api/v1/donations/{donation_id}/save", headers=user_headers)
    assert save_resp.status_code == 201

    saved_list_resp = await async_client.get("/api/v1/donations/saved", headers=user_headers)
    assert saved_list_resp.status_code == 200
    assert len(saved_list_resp.json()) >= 1

    saved_ids_resp = await async_client.get("/api/v1/donations/saved_ids", headers=user_headers)
    assert saved_ids_resp.status_code == 200
    assert donation_id in saved_ids_resp.json()

    unsave_resp = await async_client.delete(f"/api/v1/donations/{donation_id}/unsave", headers=user_headers)
    assert unsave_resp.status_code == 204

    # 6. Test SOFT DELETE
    soft_del_resp = await async_client.delete(f"/api/v1/donations/{donation_id}", headers=headers)
    assert soft_del_resp.status_code == 200
    del_data = soft_del_resp.json()
    assert del_data["status"] == "success"
    assert del_data["is_deleted"] is True
    assert del_data["permanent"] is False

    # Standard list should NOT contain the soft-deleted donation
    list_resp = await async_client.get("/api/v1/donations/")
    assert list_resp.status_code == 200
    ids_in_list = [d["id"] for d in list_resp.json()]
    assert donation_id not in ids_in_list

    # include_deleted=true should return it
    inc_resp = await async_client.get("/api/v1/donations/?include_deleted=true")
    assert inc_resp.status_code == 200
    inc_ids = [d["id"] for d in inc_resp.json()]
    assert donation_id in inc_ids

    # 7. Test RESTORE
    restore_resp = await async_client.post(f"/api/v1/donations/{donation_id}/restore", headers=headers)
    assert restore_resp.status_code == 200
    assert restore_resp.json()["is_deleted"] is False

    # Should be back in standard list
    list_after_restore = await async_client.get("/api/v1/donations/")
    assert donation_id in [d["id"] for d in list_after_restore.json()]

    # 8. Test PERMANENT DELETE
    perm_del_resp = await async_client.delete(
        f"/api/v1/donations/{donation_id}?permanent=true",
        headers=headers
    )
    assert perm_del_resp.status_code == 200
    assert perm_del_resp.json()["permanent"] is True

    # Even include_deleted=true should no longer find it
    inc_after_perm = await async_client.get("/api/v1/donations/?include_deleted=true")
    assert donation_id not in [d["id"] for d in inc_after_perm.json()]


@pytest.mark.asyncio
async def test_all_modules_crud(async_client, admin_auth, user_auth):
    adm_headers = {"Authorization": admin_auth["Authorization"]}
    usr_headers = {"Authorization": user_auth["Authorization"]}

    # --- Core Config (Features) ---
    f_res = await async_client.post(
        "/api/v1/features/",
        headers=adm_headers,
        json={"name": f"dark_mode_{int(time.time()*1000)}", "is_active": True, "description": "Dark theme"}
    )
    assert f_res.status_code == 201
    f_id = f_res.json()["id"]
    get_f = await async_client.get(f"/api/v1/features/{f_id}")
    assert get_f.status_code == 200
    del_f = await async_client.delete(f"/api/v1/features/{f_id}", headers=adm_headers)
    assert del_f.status_code == 204

    # --- Duas & Dua Categories ---
    dua_cat = await async_client.post(
        "/api/v1/duas/categories",
        headers=adm_headers,
        json={"name": "Morning & Evening", "display_order": 1}
    )
    assert dua_cat.status_code == 201
    dua_cat_id = dua_cat.json()["id"]

    dua_res = await async_client.post(
        "/api/v1/duas/",
        headers=adm_headers,
        json={
            "title": "Ayat al-Kursi",
            "arabic_text": "اللَّهُ لاَ إِلَٰهَ إِلاَّ هُوَ الْحَيُّ الْقَيُّومُ",
            "translation_en": "Allah! There is no deity except Him, the Ever-Living, the Sustainer of existence.",
            "category_id": dua_cat_id
        }
    )
    assert dua_res.status_code == 201
    dua_id = dua_res.json()["id"]

    get_dua = await async_client.get(f"/api/v1/duas/{dua_id}")
    assert get_dua.status_code == 200
    del_dua = await async_client.delete(f"/api/v1/duas/{dua_id}", headers=adm_headers)
    assert del_dua.status_code == 204

    # --- Events & Event Categories ---
    ev_cat = await async_client.post(
        "/api/v1/events/categories",
        headers=adm_headers,
        json={"name": "Youth Workshops"}
    )
    assert ev_cat.status_code == 201
    ev_cat_id = ev_cat.json()["id"]

    ev_res = await async_client.post(
        "/api/v1/events/",
        headers=adm_headers,
        json={
            "title": "Islamic Finance Seminar",
            "category_id": ev_cat_id,
            "story": "Understanding halal wealth and investments",
            "event_date": "2026-10-15",
            "start_time": "14:00:00",
            "venue_name": "Jamia Mosque Multi-purpose Hall"
        }
    )
    assert ev_res.status_code == 201
    ev_id = ev_res.json()["id"]

    ev_notify = await async_client.post(f"/api/v1/events/{ev_id}/notify", headers=adm_headers)
    assert ev_notify.status_code == 200

    # --- Khutba ---
    khutba_res = await async_client.post(
        "/api/v1/khutba/",
        headers=adm_headers,
        json={
            "khutba_date": "2026-09-04",
            "khutba_time": "12:30:00",
            "imam_name": "Sheikh Muhammad",
            "title": "The Importance of Sadaqah"
        }
    )
    assert khutba_res.status_code == 201
    k_id = khutba_res.json()["id"]
    get_k = await async_client.get(f"/api/v1/khutba/{k_id}")
    assert get_k.status_code == 200

    dev_res = await async_client.post(
        "/api/v1/khutba/register-device",
        json={"fcm_token": f"token_{int(time.time()*1000)}", "platform": "Android"}
    )
    assert dev_res.status_code == 201

    # --- Prayer Times ---
    city_res = await async_client.post(
        "/api/v1/prayer-times/cities",
        headers=adm_headers,
        json={"name": f"Mombasa_{int(time.time()*1000)}", "latitude": -4.0435, "longitude": 39.6682}
    )
    assert city_res.status_code == 201
    city_id = city_res.json()["id"]

    today_times = await async_client.get("/api/v1/prayer-times/today?city_name=Nairobi")
    assert today_times.status_code == 200
    assert "fajr" in today_times.json()

    # --- Quran ---
    rec_res = await async_client.post(
        "/api/v1/quran/reciters",
        headers=adm_headers,
        json={"name": "Mishary Rashid Alafasy", "bio": "Kuwaiti Qari"}
    )
    assert rec_res.status_code == 201
    rec_id = rec_res.json()["id"]

    audio_res = await async_client.post(
        "/api/v1/quran/audio",
        headers=adm_headers,
        json={"surah_number": 1, "reciter_id": rec_id, "audio_url": "https://example.com/001.mp3"}
    )
    assert audio_res.status_code == 201

    # --- Zakat ---
    nisab_res = await async_client.get("/api/v1/zakat/nisab")
    assert nisab_res.status_code == 200

    calc_res = await async_client.post(
        "/api/v1/zakat/calculate",
        json={
            "cash_in_hand_or_bank": 200000.0,
            "gold_grams": 50.0,
            "silver_grams": 0.0,
            "short_term_debts": 10000.0
        }
    )
    assert calc_res.status_code == 200
    calc_data = calc_res.json()
    assert "zakat_payable_kes" in calc_data
    assert calc_data["is_zakat_due"] is True

    # --- User Payment Accounts ---
    pay_acc_res = await async_client.post(
        "/api/v1/users/payment-accounts",
        headers=usr_headers,
        json={"account_type": "M-Pesa", "account_number": "0712345678", "is_default": True}
    )
    assert pay_acc_res.status_code == 201
    pay_acc_id = pay_acc_res.json()["id"]

    list_pay = await async_client.get("/api/v1/users/payment-accounts", headers=usr_headers)
    assert list_pay.status_code == 200
    assert any(a["id"] == pay_acc_id for a in list_pay.json())

    # --- Analytics ---
    summary_res = await async_client.get("/api/v1/analytics/summary", headers=adm_headers)
    assert summary_res.status_code == 200
    assert "total_collected" in summary_res.json()

    cats_analytics = await async_client.get("/api/v1/analytics/categories", headers=adm_headers)
    assert cats_analytics.status_code == 200

    trends_res = await async_client.get("/api/v1/analytics/trends?period=week", headers=adm_headers)
    assert trends_res.status_code == 200

    export_res = await async_client.get("/api/v1/analytics/export", headers=adm_headers)
    assert export_res.status_code == 200
    assert "text/csv" in export_res.headers.get("content-type", "")
