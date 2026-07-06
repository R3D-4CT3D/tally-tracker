import uuid
from datetime import date, timedelta
from typing import Any

from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.financial_year_board import FinancialYearBoard
from app.models.trophy import Trophy
from tests.conftest import SETUP_PAYLOAD


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
    assert resp.status_code == 201, resp.text
    result: str = resp.json()["id"]
    return result


async def _create_goal(client: AsyncClient, **overrides: Any) -> dict[str, Any]:
    payload = {
        "name": "Emergency Fund",
        "target_cents": 100000,
        "icon": "🐷",
        "color": "#059669",
        **overrides,
    }
    resp = await client.post("/api/v1/goals", json=payload, headers=_csrf_headers(client))
    assert resp.status_code == 201, resp.text
    result: dict[str, Any] = resp.json()
    return result


async def _create_debt(client: AsyncClient, **overrides: Any) -> dict[str, Any]:
    payload = {
        "name": "Visa Card",
        "type": "credit_card",
        "original_balance_cents": 10000,
        "current_balance_cents": 10000,
        "apr_bps": 1999,
        "min_payment_cents": 2500,
        "due_day": 15,
        **overrides,
    }
    resp = await client.post("/api/v1/debts", json=payload, headers=_csrf_headers(client))
    assert resp.status_code == 201, resp.text
    result: dict[str, Any] = resp.json()
    return result


async def test_categorizing_transaction_starts_a_streak(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    await client.post("/api/v1/setup", json=SETUP_PAYLOAD)
    account_id = await _create_account(client)
    category_resp = await client.get("/api/v1/categories")
    category_id = category_resp.json()[0]["id"]

    txn = await client.post(
        "/api/v1/transactions",
        json={
            "account_id": account_id,
            "date": "2026-01-15",
            "amount_cents": -500,
            "description": "Coffee",
        },
        headers=_csrf_headers(client),
    )
    txn_id = txn.json()["id"]

    board_before = await client.get("/api/v1/board")
    assert board_before.json()["streak"]["current_weeks"] == 0

    await client.patch(
        f"/api/v1/transactions/{txn_id}",
        json={"category_id": category_id},
        headers=_csrf_headers(client),
    )

    board_after = await client.get("/api/v1/board")
    assert board_after.json()["streak"]["current_weeks"] == 1


async def test_debt_payoff_records_a_trophy(client: AsyncClient, db_session: AsyncSession) -> None:
    await client.post("/api/v1/setup", json=SETUP_PAYLOAD)
    account_id = await _create_account(client)
    debt = await _create_debt(client, current_balance_cents=5000)

    await client.post(
        "/api/v1/transactions",
        json={
            "account_id": account_id,
            "date": "2026-01-15",
            "amount_cents": -5000,
            "description": "Payoff",
            "debt_id": debt["id"],
        },
        headers=_csrf_headers(client),
    )

    result = await db_session.execute(select(Trophy).where(Trophy.kind == "debt_payoff"))
    trophies = result.scalars().all()
    assert len(trophies) == 1
    assert trophies[0].ref_id == uuid.UUID(debt["id"])


async def test_goal_completion_records_a_trophy(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    await client.post("/api/v1/setup", json=SETUP_PAYLOAD)
    goal = await _create_goal(client, target_cents=1000)

    await client.post(
        f"/api/v1/goals/{goal['id']}/contributions",
        json={"amount_cents": 1000, "date": "2026-01-15"},
        headers=_csrf_headers(client),
    )

    result = await db_session.execute(select(Trophy).where(Trophy.kind == "goal_complete"))
    trophies = result.scalars().all()
    assert len(trophies) == 1


async def test_year_end_sets_pending_flag_and_tax_return_resolves_it(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    await client.post("/api/v1/setup", json=SETUP_PAYLOAD)
    account_id = await _create_account(client)

    # Force the board far enough back in time that lazy reconciliation
    # will consider all 52 weeks elapsed.
    await client.get("/api/v1/board")
    result = await db_session.execute(select(FinancialYearBoard))
    board = result.scalar_one()
    board.year_start_date = date.today() - timedelta(weeks=53)
    await db_session.commit()

    resp = await client.get("/api/v1/board")
    body = resp.json()
    assert body["current_week"] == 52
    assert body["year_end_pending"] is True

    # Still pending on a repeated fetch -- doesn't silently roll a new board.
    resp2 = await client.get("/api/v1/board")
    assert resp2.json()["year_end_pending"] is True
    assert resp2.json()["year_start_date"] == body["year_start_date"]

    tax_resp = await client.post(
        "/api/v1/board/tax-return",
        json={"account_id": account_id, "amount_cents": 150000},
        headers=_csrf_headers(client),
    )
    assert tax_resp.status_code == 200, tax_resp.text
    assert tax_resp.json()["year_end_pending"] is False
    assert tax_resp.json()["current_week"] == 0
    assert tax_resp.json()["year_start_date"] != body["year_start_date"]

    txns = await client.get("/api/v1/transactions")
    descriptions = [t["description_display"] for t in txns.json()["items"]]
    assert "Tax return" in descriptions


async def test_declining_tax_return_still_starts_new_board(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    await client.post("/api/v1/setup", json=SETUP_PAYLOAD)
    await client.get("/api/v1/board")
    result = await db_session.execute(select(FinancialYearBoard))
    board = result.scalar_one()
    board.year_start_date = date.today() - timedelta(weeks=53)
    await db_session.commit()

    await client.get("/api/v1/board")  # trigger reconciliation -> completed_at set

    resp = await client.post(
        "/api/v1/board/tax-return",
        json={"amount_cents": 0},
        headers=_csrf_headers(client),
    )
    assert resp.status_code == 200, resp.text
    assert resp.json()["year_end_pending"] is False
    assert resp.json()["current_week"] == 0


async def test_transaction_can_be_flagged_unexpected(client: AsyncClient) -> None:
    await client.post("/api/v1/setup", json=SETUP_PAYLOAD)
    account_id = await _create_account(client)

    resp = await client.post(
        "/api/v1/transactions",
        json={
            "account_id": account_id,
            "date": "2026-01-15",
            "amount_cents": -50000,
            "description": "Car repair",
            "flagged_unexpected": True,
        },
        headers=_csrf_headers(client),
    )
    assert resp.status_code == 201, resp.text
    assert resp.json()["flagged_unexpected"] is True
