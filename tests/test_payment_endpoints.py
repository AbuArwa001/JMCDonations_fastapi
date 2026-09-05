import pytest
import uuid
import time
from datetime import datetime, timezone, timedelta
from httpx import AsyncClient, ASGITransport
from app.main import app
from app.core.security import create_access_token
from app.models.users import User
from app.models.donations import Donation
from app.models.categories import Category
from app.models.transactions import Transaction
from app.db.session import AsyncSessionLocal
from unittest.mock import patch, AsyncMock

@pytest.fixture
async def async_client():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        yield ac

@pytest.fixture
async def sample_donation():
    async with AsyncSessionLocal() as session:
        unique_suffix = int(time.time() * 1000)
        user = User(
            email=f"test_creator_{unique_suffix}@example.com",
            username=f"creator_{unique_suffix}",
            full_name="Creator User",
            is_active=True,
            is_admin=True
        )
        session.add(user)
        await session.commit()
        await session.refresh(user)

        cat = Category(category_name=f"Relief_{unique_suffix}", color="#00C853")
        session.add(cat)
        await session.commit()
        await session.refresh(cat)

        donation = Donation(
            title=f"Test Drive {unique_suffix}",
            description="Test description",
            target_amount=100000.0,
            paybill_number="150770",
            account_name="Jamia Donation",
            account_number="ACC-100",
            start_date=datetime.now(timezone.utc).replace(tzinfo=None),
            end_date=(datetime.now(timezone.utc) + timedelta(days=30)).replace(tzinfo=None),
            category_id=cat.id,
            created_by_id=user.id,
            is_featured=True,
            is_deleted=False
        )
        session.add(donation)
        await session.commit()
        await session.refresh(donation)
        return donation


@pytest.mark.asyncio
async def test_card_payment_flow(async_client, sample_donation):
    # Test initiate_card_payment (without trailing slash)
    res = await async_client.post(
        "/api/v1/transactions/initiate_card_payment",
        json={"amount": 500.0, "donation_id": str(sample_donation.id)}
    )
    assert res.status_code == 201
    data = res.json()
    assert "tx_ref" in data
    assert data["amount"] == 500.0
    tx_ref = data["tx_ref"]

    # Test initiate_card_payment (WITH trailing slash - should not 307 redirect)
    res_slash = await async_client.post(
        "/api/v1/transactions/initiate_card_payment/",
        json={"amount": 300.0, "donation_id": str(sample_donation.id)}
    )
    assert res_slash.status_code == 201

    # Test verify_flutterwave_payment (without slash)
    verify_res = await async_client.post(
        "/api/v1/transactions/verify_flutterwave_payment",
        json={
            "tx_ref": tx_ref,
            "flw_ref": "FLW-123456",
            "amount": 500.0,
            "donation_id": str(sample_donation.id),
            "status": "successful"
        }
    )
    assert verify_res.status_code == 200
    verify_data = verify_res.json()
    assert verify_data["status"] == "Completed"

    # Test verify_flutterwave_payment (WITH trailing slash)
    verify_slash_res = await async_client.post(
        "/api/v1/transactions/verify_flutterwave_payment/",
        json={
            "tx_ref": f"TX-DIRECT-{uuid.uuid4()}",
            "flw_ref": "FLW-DIRECT-999",
            "amount": 750.0,
            "donation_id": str(sample_donation.id),
            "status": "successful"
        }
    )
    assert verify_slash_res.status_code == 200
    assert verify_slash_res.json()["status"] == "Completed"


@pytest.mark.asyncio
async def test_paypal_payment_flow(async_client, sample_donation):
    async def create_fake_order(*args, **kwargs):
        order_id = f"ORDER-{uuid.uuid4().hex[:10].upper()}"
        return {
            "id": order_id,
            "links": [
                {"href": f"https://www.sandbox.paypal.com/checkoutnow?token={order_id}", "rel": "approve"}
            ]
        }

    with patch("app.services.paypal.paypal_service.create_order", side_effect=create_fake_order):

        # Test initiate_paypal_payment (without slash)
        res = await async_client.post(
            "/api/v1/transactions/initiate_paypal_payment",
            json={"amount": 25.0, "donation": str(sample_donation.id)}
        )
        assert res.status_code == 200
        data = res.json()
        assert "approval_url" in data
        assert "transaction_id" in data
        tx_id = data["transaction_id"]

        # Test initiate_paypal_payment (WITH trailing slash)
        res_slash = await async_client.post(
            "/api/v1/transactions/initiate_paypal_payment/",
            json={"amount": 25.0, "donation": str(sample_donation.id)}
        )
        assert res_slash.status_code == 200

    # Test paypal_callback cancel
    res_cancel = await async_client.get(
        "/api/v1/transactions/paypal_callback",
        params={"tx_id": tx_id, "cancel": "true"},
        follow_redirects=False
    )
    assert res_cancel.status_code == 302
    assert res_cancel.headers["location"] == "jamiagive://payment/cancel"

    # Test paypal_callback success with capture
    mock_capture = {
        "status": "COMPLETED",
        "purchase_units": [{
            "payments": {
                "captures": [{"id": "CAPTURE-12345"}]
            }
        }]
    }
    with patch("app.services.paypal.paypal_service.capture_order", new_callable=AsyncMock) as mock_cap:
        mock_cap.return_value = mock_capture

        res_success = await async_client.get(
            "/api/v1/transactions/paypal_callback/",
            params={"tx_id": tx_id, "token": "ORDER-TEST"},
            follow_redirects=False
        )
        assert res_success.status_code == 302
        assert f"jamiagive://payment/success?tx_id={tx_id}" in res_success.headers["location"]
