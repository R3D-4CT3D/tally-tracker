from typing import Any

from httpx import AsyncClient

from tests.conftest import SETUP_PAYLOAD


def _csrf_headers(client: AsyncClient) -> dict[str, str]:
    token = client.cookies.get("tally_csrf")
    assert token is not None
    return {"X-CSRF-Token": token}


async def _create_debt(client: AsyncClient, **overrides: Any) -> dict[str, Any]:
    payload = {
        "name": "Visa Card",
        "type": "credit_card",
        "original_balance_cents": 500000,
        "current_balance_cents": 500000,
        "apr_bps": 1999,
        "min_payment_cents": 2500,
        "due_day": 15,
        **overrides,
    }
    resp = await client.post("/api/v1/debts", json=payload, headers=_csrf_headers(client))
    assert resp.status_code == 201, resp.text
    result: dict[str, Any] = resp.json()
    return result


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


async def _create_transaction(client: AsyncClient, **overrides: Any) -> dict[str, Any]:
    payload = {
        "date": "2026-01-15",
        "amount_cents": -2500,
        "description": "txn",
        **overrides,
    }
    resp = await client.post("/api/v1/transactions", json=payload, headers=_csrf_headers(client))
    assert resp.status_code == 201, resp.text
    result: dict[str, Any] = resp.json()
    return result


async def test_create_list_update_archive_debt(client: AsyncClient) -> None:
    await client.post("/api/v1/setup", json=SETUP_PAYLOAD)
    created = await _create_debt(client)
    assert created["current_balance_cents"] == 500000
    assert created["paid_off_at"] is None
    assert created["archived"] is False

    listed = await client.get("/api/v1/debts")
    assert len(listed.json()) == 1

    updated = await client.patch(
        f"/api/v1/debts/{created['id']}",
        json={"min_payment_cents": 3000},
        headers=_csrf_headers(client),
    )
    assert updated.status_code == 200
    assert updated.json()["min_payment_cents"] == 3000

    archived = await client.post(
        f"/api/v1/debts/{created['id']}/archive", headers=_csrf_headers(client)
    )
    assert archived.status_code == 200
    assert archived.json()["archived"] is True

    default_list = await client.get("/api/v1/debts")
    assert default_list.json() == []
    include_archived = await client.get("/api/v1/debts?include_archived=true")
    assert len(include_archived.json()) == 1


async def test_transaction_with_debt_id_reduces_balance(client: AsyncClient) -> None:
    await client.post("/api/v1/setup", json=SETUP_PAYLOAD)
    account_id = await _create_account(client)
    debt = await _create_debt(client, current_balance_cents=10000)

    await _create_transaction(client, account_id=account_id, amount_cents=-3000, debt_id=debt["id"])

    fetched = await client.get(f"/api/v1/debts/{debt['id']}")
    assert fetched.json()["current_balance_cents"] == 7000
    assert fetched.json()["paid_off_at"] is None


async def test_deleting_debt_linked_transaction_restores_balance(client: AsyncClient) -> None:
    await client.post("/api/v1/setup", json=SETUP_PAYLOAD)
    account_id = await _create_account(client)
    debt = await _create_debt(client, current_balance_cents=10000)

    txn = await _create_transaction(
        client, account_id=account_id, amount_cents=-3000, debt_id=debt["id"]
    )
    mid = await client.get(f"/api/v1/debts/{debt['id']}")
    assert mid.json()["current_balance_cents"] == 7000

    delete_resp = await client.delete(
        f"/api/v1/transactions/{txn['id']}", headers=_csrf_headers(client)
    )
    assert delete_resp.status_code == 204

    after = await client.get(f"/api/v1/debts/{debt['id']}")
    assert after.json()["current_balance_cents"] == 10000


async def test_updating_debt_linked_transaction_amount_adjusts_balance(client: AsyncClient) -> None:
    await client.post("/api/v1/setup", json=SETUP_PAYLOAD)
    account_id = await _create_account(client)
    debt = await _create_debt(client, current_balance_cents=10000)

    txn = await _create_transaction(
        client, account_id=account_id, amount_cents=-3000, debt_id=debt["id"]
    )
    await client.patch(
        f"/api/v1/transactions/{txn['id']}",
        json={"amount_cents": -5000},
        headers=_csrf_headers(client),
    )

    after = await client.get(f"/api/v1/debts/{debt['id']}")
    assert after.json()["current_balance_cents"] == 5000


async def test_reassigning_transaction_to_a_different_debt_adjusts_both(
    client: AsyncClient,
) -> None:
    await client.post("/api/v1/setup", json=SETUP_PAYLOAD)
    account_id = await _create_account(client)
    debt_a = await _create_debt(client, name="Card A", current_balance_cents=10000)
    debt_b = await _create_debt(client, name="Card B", current_balance_cents=20000)

    txn = await _create_transaction(
        client, account_id=account_id, amount_cents=-3000, debt_id=debt_a["id"]
    )
    await client.patch(
        f"/api/v1/transactions/{txn['id']}",
        json={"debt_id": debt_b["id"]},
        headers=_csrf_headers(client),
    )

    after_a = await client.get(f"/api/v1/debts/{debt_a['id']}")
    after_b = await client.get(f"/api/v1/debts/{debt_b['id']}")
    assert after_a.json()["current_balance_cents"] == 10000
    assert after_b.json()["current_balance_cents"] == 17000


async def test_debt_paid_off_at_set_when_balance_reaches_zero_and_cleared_on_reopen(
    client: AsyncClient,
) -> None:
    await client.post("/api/v1/setup", json=SETUP_PAYLOAD)
    account_id = await _create_account(client)
    debt = await _create_debt(client, current_balance_cents=5000)

    payoff_txn = await _create_transaction(
        client, account_id=account_id, amount_cents=-5000, debt_id=debt["id"]
    )
    paid_off = await client.get(f"/api/v1/debts/{debt['id']}")
    assert paid_off.json()["current_balance_cents"] == 0
    assert paid_off.json()["paid_off_at"] is not None

    # Deleting the payoff transaction reopens the debt -- paid_off_at is
    # symmetric, not a one-way ratchet.
    await client.delete(f"/api/v1/transactions/{payoff_txn['id']}", headers=_csrf_headers(client))
    reopened = await client.get(f"/api/v1/debts/{debt['id']}")
    assert reopened.json()["current_balance_cents"] == 5000
    assert reopened.json()["paid_off_at"] is None


async def test_positive_amount_on_debt_linked_transaction_increases_balance(
    client: AsyncClient,
) -> None:
    """A debt-linked transaction isn't always a payment -- a positive amount
    (new charge/refund) legitimately increases current_balance_cents, and
    must not be rejected.
    """
    await client.post("/api/v1/setup", json=SETUP_PAYLOAD)
    account_id = await _create_account(client)
    debt = await _create_debt(client, current_balance_cents=5000)

    resp = await _create_transaction(
        client, account_id=account_id, amount_cents=2000, debt_id=debt["id"]
    )
    assert resp["debt_id"] == debt["id"]

    after = await client.get(f"/api/v1/debts/{debt['id']}")
    assert after.json()["current_balance_cents"] == 7000
