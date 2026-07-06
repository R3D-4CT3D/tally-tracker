from typing import Any

from httpx import AsyncClient

from tests.conftest import SETUP_PAYLOAD


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


async def _create_debt(client: AsyncClient, **overrides: Any) -> dict[str, Any]:
    payload = {
        "name": "Visa Card",
        "type": "credit_card",
        "original_balance_cents": 500000,
        "current_balance_cents": 500000,
        "apr_bps": 1999,
        "min_payment_cents": 5000,
        "due_day": 1,
        **overrides,
    }
    resp = await client.post("/api/v1/debts", json=payload, headers=_csrf_headers(client))
    assert resp.status_code == 201, resp.text
    result: dict[str, Any] = resp.json()
    return result


async def test_first_fetch_creates_board_starting_at_week_zero(client: AsyncClient) -> None:
    await client.post("/api/v1/setup", json=SETUP_PAYLOAD)

    resp = await client.get("/api/v1/board")
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["current_week"] == 0
    assert body["board_size"] == 52
    assert len(body["tiles"]) == 52
    assert body["tiles"][0]["kind"] == "go"
    assert body["tiles"][0]["is_current"] is True
    assert body["streak"] == {"current_weeks": 0, "best_weeks": 0, "freezes_banked": 0}


async def test_board_is_stable_across_repeated_fetches(client: AsyncClient) -> None:
    await client.post("/api/v1/setup", json=SETUP_PAYLOAD)

    first = await client.get("/api/v1/board")
    second = await client.get("/api/v1/board")
    assert first.json()["year_start_date"] == second.json()["year_start_date"]
    assert first.json()["current_week"] == second.json()["current_week"]


async def test_goal_and_debt_appear_as_property_and_mortgage_tiles(client: AsyncClient) -> None:
    await client.post("/api/v1/setup", json=SETUP_PAYLOAD)
    goal = await _create_goal(client)
    debt = await _create_debt(client)

    resp = await client.get("/api/v1/board")
    tiles = resp.json()["tiles"]

    property_tiles = [t for t in tiles if t["kind"] == "property"]
    mortgage_tiles = [t for t in tiles if t["kind"] == "mortgage"]
    assert len(property_tiles) == 1
    assert len(mortgage_tiles) == 1
    assert property_tiles[0]["ref_id"] == goal["id"]
    assert property_tiles[0]["label"] == "Emergency Fund"
    assert property_tiles[0]["owned"] is False
    assert mortgage_tiles[0]["ref_id"] == debt["id"]
    assert mortgage_tiles[0]["owned"] is False


async def test_archived_debt_excluded_from_board(client: AsyncClient) -> None:
    await client.post("/api/v1/setup", json=SETUP_PAYLOAD)
    debt = await _create_debt(client)
    await client.post(f"/api/v1/debts/{debt['id']}/archive", headers=_csrf_headers(client))

    resp = await client.get("/api/v1/board")
    tiles = resp.json()["tiles"]
    assert not [t for t in tiles if t["kind"] == "mortgage"]


async def test_board_has_exactly_one_go_jail_and_free_parking_tile(client: AsyncClient) -> None:
    await client.post("/api/v1/setup", json=SETUP_PAYLOAD)

    resp = await client.get("/api/v1/board")
    tiles = resp.json()["tiles"]
    kinds = [t["kind"] for t in tiles]
    assert kinds.count("go") == 1
    assert kinds.count("jail") == 1
    assert kinds.count("free_parking") == 1
    assert kinds.count("chest") == 12
    assert kinds.count("chance") == 4
    assert kinds.count("tax") == 2
    # every index appears exactly once, 0..51
    assert sorted(t["index"] for t in tiles) == list(range(52))


async def test_board_requires_auth(client: AsyncClient) -> None:
    resp = await client.get("/api/v1/board")
    assert resp.status_code == 401
