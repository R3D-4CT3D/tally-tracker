
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
    assert resp.status_code == 201, resp.text
    result: str = resp.json()["id"]
    return result


async def test_preview_reflects_month_transactions(client: AsyncClient) -> None:
    await client.post("/api/v1/setup", json=SETUP_PAYLOAD)
    account_id = await _create_account(client)

    await client.post(
        "/api/v1/transactions",
        json={
            "account_id": account_id,
            "date": "2026-03-10",
            "amount_cents": -5000,
            "description": "Groceries",
        },
        headers=_csrf_headers(client),
    )
    await client.post(
        "/api/v1/transactions",
        json={
            "account_id": account_id,
            "date": "2026-03-15",
            "amount_cents": 200000,
            "description": "Paycheck",
        },
        headers=_csrf_headers(client),
    )

    resp = await client.get("/api/v1/monthly-close/preview", params={"month": "2026-03-01"})
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["income_cents"] == 200000
    assert body["spend_cents"] == 5000
    assert body["uncategorized_count"] == 2
    assert body["grade"] in {"A", "B", "C", "D"}


async def test_complete_persists_and_is_idempotent(client: AsyncClient) -> None:
    await client.post("/api/v1/setup", json=SETUP_PAYLOAD)

    resp = await client.post(
        "/api/v1/monthly-close/complete",
        json={"month": "2026-03-01"},
        headers=_csrf_headers(client),
    )
    assert resp.status_code == 200, resp.text
    first = resp.json()
    assert first["month"] == "2026-03-01"

    # Re-completing the same month overwrites rather than erroring or
    # creating a second row.
    resp2 = await client.post(
        "/api/v1/monthly-close/complete",
        json={"month": "2026-03-01"},
        headers=_csrf_headers(client),
    )
    assert resp2.status_code == 200, resp2.text
    assert resp2.json()["id"] == first["id"]

    listed = await client.get("/api/v1/monthly-close")
    assert len(listed.json()) == 1


async def test_get_before_completion_is_404(client: AsyncClient) -> None:
    await client.post("/api/v1/setup", json=SETUP_PAYLOAD)
    resp = await client.get("/api/v1/monthly-close/2026-03-01")
    assert resp.status_code == 404


async def test_completing_counts_as_checkin_and_viewing_counts_for_second_user(
    client: AsyncClient, db_session: AsyncSession, fake_redis: Redis
) -> None:
    household_id, _, _, session_a = await seed_household(
        db_session, fake_redis, household_name="Shared House", owner_email="close-a@example.com"
    )
    apply_session_cookies(client, session_a)

    board_before = await client.get("/api/v1/board")
    assert board_before.json()["streak"]["current_weeks"] == 0

    await client.post(
        "/api/v1/monthly-close/complete",
        json={"month": "2026-03-01"},
        headers={"X-CSRF-Token": session_a.csrf_token},
    )

    board_after = await client.get("/api/v1/board")
    assert board_after.json()["streak"]["current_weeks"] == 1


async def test_monthly_close_is_household_scoped(
    client: AsyncClient, db_session: AsyncSession, fake_redis: Redis
) -> None:
    _, _, _, session_a = await seed_household(
        db_session, fake_redis, household_name="Household A", owner_email="mca@example.com"
    )
    _, _, _, session_b = await seed_household(
        db_session, fake_redis, household_name="Household B", owner_email="mcb@example.com"
    )

    apply_session_cookies(client, session_a)
    await client.post(
        "/api/v1/monthly-close/complete",
        json={"month": "2026-03-01"},
        headers={"X-CSRF-Token": session_a.csrf_token},
    )

    apply_session_cookies(client, session_b)
    resp = await client.get("/api/v1/monthly-close/2026-03-01")
    assert resp.status_code == 404
