from typing import Any

from httpx import AsyncClient

from tests.conftest import SETUP_PAYLOAD


def _csrf_headers(client: AsyncClient) -> dict[str, str]:
    token = client.cookies.get("tally_csrf")
    assert token is not None
    return {"X-CSRF-Token": token}


async def _create_category(client: AsyncClient, **overrides: Any) -> dict[str, Any]:
    payload = {"name": "Custom", "icon": "star", "color": "#ABCDEF", **overrides}
    resp = await client.post("/api/v1/categories", json=payload, headers=_csrf_headers(client))
    assert resp.status_code == 201, resp.text
    result: dict[str, Any] = resp.json()
    return result


async def test_setup_seeds_default_categories(client: AsyncClient) -> None:
    await client.post("/api/v1/setup", json=SETUP_PAYLOAD)
    resp = await client.get("/api/v1/categories")
    assert resp.status_code == 200
    categories = resp.json()
    assert len(categories) == 14
    assert all(c["is_system"] is True for c in categories)
    assert {c["name"] for c in categories} == {
        "Housing",
        "Utilities",
        "Groceries",
        "Dining",
        "Transport",
        "Insurance",
        "Subscriptions",
        "Health",
        "Entertainment",
        "Debt Payment",
        "Savings",
        "Income",
        "Fees",
        "Misc",
    }


async def test_create_user_category(client: AsyncClient) -> None:
    await client.post("/api/v1/setup", json=SETUP_PAYLOAD)
    created = await _create_category(client, name="Hobbies")
    assert created["name"] == "Hobbies"
    assert created["is_system"] is False
    assert created["parent_id"] is None


async def test_create_subcategory_under_parent(client: AsyncClient) -> None:
    await client.post("/api/v1/setup", json=SETUP_PAYLOAD)
    parent = await _create_category(client, name="Parent")
    child = await _create_category(client, name="Child", parent_id=parent["id"])
    assert child["parent_id"] == parent["id"]


async def test_subcategory_of_subcategory_is_rejected(client: AsyncClient) -> None:
    await client.post("/api/v1/setup", json=SETUP_PAYLOAD)
    parent = await _create_category(client, name="Parent")
    child = await _create_category(client, name="Child", parent_id=parent["id"])

    resp = await client.post(
        "/api/v1/categories",
        json={"name": "Grandchild", "icon": "star", "color": "#ABCDEF", "parent_id": child["id"]},
        headers=_csrf_headers(client),
    )
    assert resp.status_code == 400


async def test_category_parent_must_exist(client: AsyncClient) -> None:
    await client.post("/api/v1/setup", json=SETUP_PAYLOAD)
    resp = await client.post(
        "/api/v1/categories",
        json={
            "name": "Orphan",
            "icon": "star",
            "color": "#ABCDEF",
            "parent_id": "00000000-0000-0000-0000-000000000000",
        },
        headers=_csrf_headers(client),
    )
    assert resp.status_code == 400


async def test_update_category(client: AsyncClient) -> None:
    await client.post("/api/v1/setup", json=SETUP_PAYLOAD)
    created = await _create_category(client, name="Original")
    resp = await client.patch(
        f"/api/v1/categories/{created['id']}",
        json={"name": "Renamed"},
        headers=_csrf_headers(client),
    )
    assert resp.status_code == 200
    assert resp.json()["name"] == "Renamed"
    assert resp.json()["color"] == created["color"]


async def test_category_with_children_cannot_become_a_subcategory(client: AsyncClient) -> None:
    await client.post("/api/v1/setup", json=SETUP_PAYLOAD)
    parent = await _create_category(client, name="Parent")
    other = await _create_category(client, name="Other")
    await _create_category(client, name="Child", parent_id=parent["id"])

    resp = await client.patch(
        f"/api/v1/categories/{parent['id']}",
        json={"parent_id": other["id"]},
        headers=_csrf_headers(client),
    )
    assert resp.status_code == 400


async def test_update_category_not_found(client: AsyncClient) -> None:
    await client.post("/api/v1/setup", json=SETUP_PAYLOAD)
    resp = await client.patch(
        "/api/v1/categories/00000000-0000-0000-0000-000000000000",
        json={"name": "Nope"},
        headers=_csrf_headers(client),
    )
    assert resp.status_code == 404
