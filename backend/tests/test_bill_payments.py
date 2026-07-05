from typing import Any

from httpx import AsyncClient
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from tests.conftest import SETUP_PAYLOAD, apply_session_cookies, seed_household


def _csrf_headers(client: AsyncClient) -> dict[str, str]:
    token = client.cookies.get("tally_csrf")
    assert token is not None
    return {"X-CSRF-Token": token}


async def _create_account(client: AsyncClient) -> str:
    resp = await client.post(
        "/api/v1/accounts",
        json={
            "name": "Checking",
            "type": "checking",
            "balance_cents": 0,
            "color": "#336699",
            "icon": "bank",
        },
        headers=_csrf_headers(client),
    )
    assert resp.status_code == 201
    account_id: str = resp.json()["id"]
    return account_id


async def _create_bill(client: AsyncClient, **overrides: Any) -> dict[str, Any]:
    payload = {
        "name": "Electric",
        "amount_cents": 12000,
        "is_variable": False,
        "frequency": "monthly",
        "due_day": 15,
        "autopay": False,
        "next_due_date": "2026-01-15",
        **overrides,
    }
    resp = await client.post("/api/v1/bills", json=payload, headers=_csrf_headers(client))
    assert resp.status_code == 201, resp.text
    result: dict[str, Any] = resp.json()
    return result


async def _create_transaction(client: AsyncClient, **overrides: Any) -> dict[str, Any]:
    payload = {
        "date": "2026-01-15",
        "amount_cents": -12000,
        "description": "Electric payment",
        **overrides,
    }
    resp = await client.post("/api/v1/transactions", json=payload, headers=_csrf_headers(client))
    assert resp.status_code == 201, resp.text
    result: dict[str, Any] = resp.json()
    return result


async def test_mark_paid_link_path_advances_due_date(client: AsyncClient) -> None:
    await client.post("/api/v1/setup", json=SETUP_PAYLOAD)
    account_id = await _create_account(client)
    bill = await _create_bill(client)
    txn = await _create_transaction(client, account_id=account_id)

    resp = await client.post(
        f"/api/v1/bills/{bill['id']}/mark-paid",
        json={"transaction_id": txn["id"]},
        headers=_csrf_headers(client),
    )
    assert resp.status_code == 201, resp.text
    payment = resp.json()
    assert payment["transaction_id"] == txn["id"]
    assert payment["status"] == "paid"
    assert payment["amount_cents"] == -12000

    updated_bill = await client.get(f"/api/v1/bills/{bill['id']}")
    assert updated_bill.json()["next_due_date"] == "2026-02-15"

    history = await client.get(f"/api/v1/bills/{bill['id']}/payments")
    assert len(history.json()) == 1


async def test_mark_paid_quick_create_path_creates_transaction(client: AsyncClient) -> None:
    await client.post("/api/v1/setup", json=SETUP_PAYLOAD)
    account_id = await _create_account(client)
    bill = await _create_bill(client)

    resp = await client.post(
        f"/api/v1/bills/{bill['id']}/mark-paid",
        json={"account_id": account_id, "amount_cents": -12000, "date": "2026-01-14"},
        headers=_csrf_headers(client),
    )
    assert resp.status_code == 201, resp.text
    payment = resp.json()
    assert payment["transaction_id"] is not None

    txn_resp = await client.get(f"/api/v1/transactions/{payment['transaction_id']}")
    assert txn_resp.status_code == 200
    assert txn_resp.json()["amount_cents"] == -12000

    updated_bill = await client.get(f"/api/v1/bills/{bill['id']}")
    assert updated_bill.json()["next_due_date"] == "2026-02-15"


async def test_mark_paid_quick_create_missing_fields_rejected(client: AsyncClient) -> None:
    await client.post("/api/v1/setup", json=SETUP_PAYLOAD)
    bill = await _create_bill(client)

    resp = await client.post(
        f"/api/v1/bills/{bill['id']}/mark-paid",
        json={},
        headers=_csrf_headers(client),
    )
    assert resp.status_code == 400


async def test_mark_paid_link_path_rejects_cross_household_transaction(
    client: AsyncClient, db_session: AsyncSession, fake_redis: Redis
) -> None:
    _, _, _, session_a = await seed_household(
        db_session, fake_redis, household_name="Household A", owner_email="billsa@example.com"
    )
    _, _, _, session_b = await seed_household(
        db_session, fake_redis, household_name="Household B", owner_email="billsb@example.com"
    )

    apply_session_cookies(client, session_a)
    account_a = await _create_account(client)
    txn_a = await _create_transaction(client, account_id=account_a)

    apply_session_cookies(client, session_b)
    bill_b = await _create_bill(client)

    resp = await client.post(
        f"/api/v1/bills/{bill_b['id']}/mark-paid",
        json={"transaction_id": txn_a["id"]},
        headers={"X-CSRF-Token": session_b.csrf_token},
    )
    assert resp.status_code == 404


async def test_mark_paid_quick_create_rejects_cross_household_account(
    client: AsyncClient, db_session: AsyncSession, fake_redis: Redis
) -> None:
    _, _, _, session_a = await seed_household(
        db_session, fake_redis, household_name="Household A", owner_email="billsa2@example.com"
    )
    _, _, _, session_b = await seed_household(
        db_session, fake_redis, household_name="Household B", owner_email="billsb2@example.com"
    )

    apply_session_cookies(client, session_a)
    account_a = await _create_account(client)

    apply_session_cookies(client, session_b)
    bill_b = await _create_bill(client)

    resp = await client.post(
        f"/api/v1/bills/{bill_b['id']}/mark-paid",
        json={"account_id": account_a, "amount_cents": -12000, "date": "2026-01-14"},
        headers={"X-CSRF-Token": session_b.csrf_token},
    )
    assert resp.status_code == 404
