from typing import Any

from httpx import AsyncClient
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from tests.conftest import SETUP_PAYLOAD, apply_session_cookies, seed_household


def _csrf_headers(client: AsyncClient) -> dict[str, str]:
    token = client.cookies.get("tally_csrf")
    assert token is not None
    return {"X-CSRF-Token": token}


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


async def test_create_list_update_delete_goal(client: AsyncClient) -> None:
    await client.post("/api/v1/setup", json=SETUP_PAYLOAD)
    created = await _create_goal(client)
    assert created["current_cents"] == 0
    assert created["completed_at"] is None

    listed = await client.get("/api/v1/goals")
    assert len(listed.json()) == 1

    updated = await client.patch(
        f"/api/v1/goals/{created['id']}",
        json={"target_cents": 200000},
        headers=_csrf_headers(client),
    )
    assert updated.status_code == 200
    assert updated.json()["target_cents"] == 200000

    deleted = await client.delete(
        f"/api/v1/goals/{created['id']}", headers=_csrf_headers(client)
    )
    assert deleted.status_code == 204

    after = await client.get("/api/v1/goals")
    assert after.json() == []


async def test_recording_contribution_increments_current_cents(client: AsyncClient) -> None:
    await client.post("/api/v1/setup", json=SETUP_PAYLOAD)
    goal = await _create_goal(client, target_cents=100000)

    resp = await client.post(
        f"/api/v1/goals/{goal['id']}/contributions",
        json={"amount_cents": 25000, "date": "2026-01-15"},
        headers=_csrf_headers(client),
    )
    assert resp.status_code == 201, resp.text

    fetched = await client.get(f"/api/v1/goals/{goal['id']}")
    assert fetched.json()["current_cents"] == 25000
    assert fetched.json()["completed_at"] is None

    history = await client.get(f"/api/v1/goals/{goal['id']}/contributions")
    assert len(history.json()) == 1


async def test_contribution_reaching_target_sets_completed_at(client: AsyncClient) -> None:
    await client.post("/api/v1/setup", json=SETUP_PAYLOAD)
    goal = await _create_goal(client, target_cents=50000, current_cents=40000)

    resp = await client.post(
        f"/api/v1/goals/{goal['id']}/contributions",
        json={"amount_cents": 10000, "date": "2026-01-15"},
        headers=_csrf_headers(client),
    )
    assert resp.status_code == 201

    fetched = await client.get(f"/api/v1/goals/{goal['id']}")
    assert fetched.json()["current_cents"] == 50000
    assert fetched.json()["completed_at"] is not None


async def test_contribution_rejects_cross_household_transaction(
    client: AsyncClient, db_session: AsyncSession, fake_redis: Redis
) -> None:
    _, _, _, session_a = await seed_household(
        db_session, fake_redis, household_name="Household A", owner_email="goalsa@example.com"
    )
    _, _, _, session_b = await seed_household(
        db_session, fake_redis, household_name="Household B", owner_email="goalsb@example.com"
    )

    apply_session_cookies(client, session_a)
    account_resp = await client.post(
        "/api/v1/accounts",
        json={
            "name": "A's Checking",
            "type": "checking",
            "balance_cents": 0,
            "color": "#336699",
            "icon": "bank",
        },
        headers={"X-CSRF-Token": session_a.csrf_token},
    )
    account_a = account_resp.json()["id"]
    txn_resp = await client.post(
        "/api/v1/transactions",
        json={
            "account_id": account_a,
            "date": "2026-01-15",
            "amount_cents": -500,
            "description": "A's transaction",
        },
        headers={"X-CSRF-Token": session_a.csrf_token},
    )
    txn_a = txn_resp.json()["id"]

    apply_session_cookies(client, session_b)
    goal_b = await _create_goal(client)

    resp = await client.post(
        f"/api/v1/goals/{goal_b['id']}/contributions",
        json={"amount_cents": 500, "date": "2026-01-15", "transaction_id": txn_a},
        headers={"X-CSRF-Token": session_b.csrf_token},
    )
    assert resp.status_code == 404
