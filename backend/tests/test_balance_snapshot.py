from datetime import date

from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.jobs.balance_snapshot import run_balance_snapshot
from tests.conftest import SETUP_PAYLOAD


def _csrf_headers(client: AsyncClient) -> dict[str, str]:
    token = client.cookies.get("tally_csrf")
    assert token is not None
    return {"X-CSRF-Token": token}


async def _create_account(client: AsyncClient, balance_cents: int) -> str:
    resp = await client.post(
        "/api/v1/accounts",
        json={
            "name": "Account",
            "type": "checking",
            "balance_cents": balance_cents,
            "color": "#336699",
            "icon": "bank",
        },
        headers=_csrf_headers(client),
    )
    assert resp.status_code == 201
    account_id: str = resp.json()["id"]
    return account_id


async def _create_debt(client: AsyncClient, current_balance_cents: int) -> str:
    resp = await client.post(
        "/api/v1/debts",
        json={
            "name": "Card",
            "type": "credit_card",
            "original_balance_cents": current_balance_cents,
            "current_balance_cents": current_balance_cents,
            "apr_bps": 1999,
            "min_payment_cents": 2500,
            "due_day": 15,
        },
        headers=_csrf_headers(client),
    )
    assert resp.status_code == 201
    debt_id: str = resp.json()["id"]
    return debt_id


async def test_run_balance_snapshot_excludes_archived_and_paid_off(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    await client.post("/api/v1/setup", json=SETUP_PAYLOAD)

    await _create_account(client, 20000)
    await _create_account(client, 30000)
    archived_account = await _create_account(client, 99999)
    await client.post(
        f"/api/v1/accounts/{archived_account}/archive", headers=_csrf_headers(client)
    )

    await _create_debt(client, 10000)
    archived_debt = await _create_debt(client, 5000)
    await client.post(f"/api/v1/debts/{archived_debt}/archive", headers=_csrf_headers(client))

    paid_off_account = await _create_account(client, 0)
    paid_off_debt = await _create_debt(client, 100)
    await client.post(
        "/api/v1/transactions",
        json={
            "account_id": paid_off_account,
            "date": "2026-01-10",
            "amount_cents": -100,
            "description": "Payoff",
            "debt_id": paid_off_debt,
        },
        headers=_csrf_headers(client),
    )

    snapshots = await run_balance_snapshot(db_session, as_of=date(2026, 1, 20))
    await db_session.commit()

    assert len(snapshots) == 1
    snapshot = snapshots[0]
    assert snapshot.cash_cents == 20000 + 30000 + 0
    assert snapshot.debt_cents == 10000


async def test_run_balance_snapshot_is_idempotent_same_day(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    await client.post("/api/v1/setup", json=SETUP_PAYLOAD)
    await _create_account(client, 10000)

    first = await run_balance_snapshot(db_session, as_of=date(2026, 1, 20))
    await db_session.commit()
    assert len(first) == 1
    assert first[0].cash_cents == 10000

    await _create_account(client, 5000)
    second = await run_balance_snapshot(db_session, as_of=date(2026, 1, 20))
    await db_session.commit()

    assert len(second) == 1
    assert second[0].id == first[0].id
    assert second[0].cash_cents == 15000

    listed = await client.get("/api/v1/balance-snapshots")
    assert len(listed.json()) == 1
    assert listed.json()[0]["cash_cents"] == 15000
