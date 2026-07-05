from typing import Any

from httpx import AsyncClient

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
    assert resp.status_code == 201
    account_id: str = resp.json()["id"]
    return account_id


async def _get_category_id(client: AsyncClient, name: str) -> str:
    resp = await client.get("/api/v1/categories")
    category_id: str = next(c["id"] for c in resp.json() if c["name"] == name)
    return category_id


async def _create_transaction(client: AsyncClient, **overrides: Any) -> dict[str, Any]:
    payload = {
        "date": "2026-01-15",
        "amount_cents": -2500,
        "description": "Coffee shop",
        **overrides,
    }
    resp = await client.post("/api/v1/transactions", json=payload, headers=_csrf_headers(client))
    assert resp.status_code == 201, resp.text
    result: dict[str, Any] = resp.json()
    return result


async def test_create_and_get_transaction(client: AsyncClient) -> None:
    await client.post("/api/v1/setup", json=SETUP_PAYLOAD)
    account_id = await _create_account(client)
    created = await _create_transaction(client, account_id=account_id)
    assert created["amount_cents"] == -2500
    assert created["description_raw"] == "Coffee shop"
    assert created["source"] == "manual"

    fetched = await client.get(f"/api/v1/transactions/{created['id']}")
    assert fetched.status_code == 200
    assert fetched.json()["id"] == created["id"]


async def test_duplicate_transaction_is_rejected(client: AsyncClient) -> None:
    await client.post("/api/v1/setup", json=SETUP_PAYLOAD)
    account_id = await _create_account(client)
    await _create_transaction(client, account_id=account_id)

    resp = await client.post(
        "/api/v1/transactions",
        json={
            "account_id": account_id,
            "date": "2026-01-15",
            "amount_cents": -2500,
            "description": "  COFFEE shop  ",
        },
        headers=_csrf_headers(client),
    )
    assert resp.status_code == 409


async def test_update_transaction_category(client: AsyncClient) -> None:
    await client.post("/api/v1/setup", json=SETUP_PAYLOAD)
    account_id = await _create_account(client)
    created = await _create_transaction(client, account_id=account_id)
    category_id = await _get_category_id(client, "Dining")

    resp = await client.patch(
        f"/api/v1/transactions/{created['id']}",
        json={"category_id": category_id},
        headers=_csrf_headers(client),
    )
    assert resp.status_code == 200
    assert resp.json()["category_id"] == category_id


async def test_update_transaction_clears_category_with_explicit_null(client: AsyncClient) -> None:
    await client.post("/api/v1/setup", json=SETUP_PAYLOAD)
    account_id = await _create_account(client)
    category_id = await _get_category_id(client, "Dining")
    created = await _create_transaction(client, account_id=account_id, category_id=category_id)

    resp = await client.patch(
        f"/api/v1/transactions/{created['id']}",
        json={"category_id": None},
        headers=_csrf_headers(client),
    )
    assert resp.status_code == 200
    assert resp.json()["category_id"] is None


async def test_delete_transaction(client: AsyncClient) -> None:
    await client.post("/api/v1/setup", json=SETUP_PAYLOAD)
    account_id = await _create_account(client)
    created = await _create_transaction(client, account_id=account_id)

    delete_resp = await client.delete(
        f"/api/v1/transactions/{created['id']}", headers=_csrf_headers(client)
    )
    assert delete_resp.status_code == 204

    get_resp = await client.get(f"/api/v1/transactions/{created['id']}")
    assert get_resp.status_code == 404


async def test_list_filters_by_account(client: AsyncClient) -> None:
    await client.post("/api/v1/setup", json=SETUP_PAYLOAD)
    account_a = await _create_account(client)
    account_b = await _create_account(client)
    await _create_transaction(client, account_id=account_a, description="A txn")
    await _create_transaction(client, account_id=account_b, description="B txn")

    resp = await client.get(f"/api/v1/transactions?account_id={account_a}")
    assert resp.status_code == 200
    items = resp.json()["items"]
    assert len(items) == 1
    assert items[0]["account_id"] == account_a


async def test_list_filters_by_category_and_uncategorized(client: AsyncClient) -> None:
    await client.post("/api/v1/setup", json=SETUP_PAYLOAD)
    account_id = await _create_account(client)
    dining_id = await _get_category_id(client, "Dining")
    await _create_transaction(
        client, account_id=account_id, description="Categorized", category_id=dining_id
    )
    await _create_transaction(client, account_id=account_id, description="Uncategorized")

    by_category = await client.get(f"/api/v1/transactions?category_id={dining_id}")
    assert [i["description_raw"] for i in by_category.json()["items"]] == ["Categorized"]

    uncategorized = await client.get("/api/v1/transactions?uncategorized=true")
    assert [i["description_raw"] for i in uncategorized.json()["items"]] == ["Uncategorized"]


async def test_list_filters_by_date_range(client: AsyncClient) -> None:
    await client.post("/api/v1/setup", json=SETUP_PAYLOAD)
    account_id = await _create_account(client)
    await _create_transaction(client, account_id=account_id, date="2026-01-01", description="Jan 1")
    await _create_transaction(client, account_id=account_id, date="2026-02-01", description="Feb 1")
    await _create_transaction(client, account_id=account_id, date="2026-03-01", description="Mar 1")

    resp = await client.get(
        "/api/v1/transactions?date_from=2026-01-15&date_to=2026-02-15"
    )
    items = resp.json()["items"]
    assert [i["description_raw"] for i in items] == ["Feb 1"]


async def test_list_search_matches_description(client: AsyncClient) -> None:
    await client.post("/api/v1/setup", json=SETUP_PAYLOAD)
    account_id = await _create_account(client)
    await _create_transaction(client, account_id=account_id, description="Grocery Store")
    await _create_transaction(client, account_id=account_id, description="Gas Station")

    resp = await client.get("/api/v1/transactions?search=grocery")
    items = resp.json()["items"]
    assert len(items) == 1
    assert items[0]["description_raw"] == "Grocery Store"


async def test_create_transaction_with_debt_id_populates_it(client: AsyncClient) -> None:
    await client.post("/api/v1/setup", json=SETUP_PAYLOAD)
    account_id = await _create_account(client)
    debt_resp = await client.post(
        "/api/v1/debts",
        json={
            "name": "Visa",
            "type": "credit_card",
            "original_balance_cents": 10000,
            "current_balance_cents": 10000,
            "apr_bps": 1999,
            "min_payment_cents": 2500,
            "due_day": 15,
        },
        headers=_csrf_headers(client),
    )
    debt_id = debt_resp.json()["id"]

    created = await _create_transaction(client, account_id=account_id, debt_id=debt_id)
    assert created["debt_id"] == debt_id

    updated = await client.patch(
        f"/api/v1/transactions/{created['id']}",
        json={"debt_id": None},
        headers=_csrf_headers(client),
    )
    assert updated.status_code == 200
    assert updated.json()["debt_id"] is None


async def test_list_pagination_cursor_walks_all_pages_without_overlap(client: AsyncClient) -> None:
    await client.post("/api/v1/setup", json=SETUP_PAYLOAD)
    account_id = await _create_account(client)
    for day in range(1, 6):
        await _create_transaction(
            client,
            account_id=account_id,
            date=f"2026-01-{day:02d}",
            description=f"Txn {day}",
        )

    seen_ids: list[str] = []
    cursor: str | None = None
    for _ in range(10):
        url = "/api/v1/transactions?limit=2"
        if cursor:
            url += f"&cursor={cursor}"
        resp = await client.get(url)
        assert resp.status_code == 200
        body = resp.json()
        seen_ids.extend(item["id"] for item in body["items"])
        cursor = body["next_cursor"]
        if cursor is None:
            break

    assert len(seen_ids) == 5
    assert len(set(seen_ids)) == 5

    all_resp = await client.get("/api/v1/transactions?limit=100")
    all_dates = [item["date"] for item in all_resp.json()["items"]]
    assert all_dates == sorted(all_dates, reverse=True)
