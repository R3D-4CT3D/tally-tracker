from typing import Any

from httpx import AsyncClient

from tests.conftest import SETUP_PAYLOAD


def _csrf_headers(client: AsyncClient) -> dict[str, str]:
    token = client.cookies.get("tally_csrf")
    assert token is not None
    return {"X-CSRF-Token": token}


async def _create_account(client: AsyncClient, **overrides: Any) -> dict[str, Any]:
    payload = {
        "name": "Checking",
        "type": "checking",
        "institution": "Test Bank",
        "balance_cents": 10000,
        "color": "#336699",
        "icon": "bank",
        **overrides,
    }
    resp = await client.post("/api/v1/accounts", json=payload, headers=_csrf_headers(client))
    assert resp.status_code == 201, resp.text
    result: dict[str, Any] = resp.json()
    return result


async def test_create_and_list_account(client: AsyncClient) -> None:
    await client.post("/api/v1/setup", json=SETUP_PAYLOAD)
    created = await _create_account(client)
    assert created["name"] == "Checking"
    assert created["type"] == "checking"
    assert created["balance_cents"] == 10000
    assert created["archived"] is False

    listed = await client.get("/api/v1/accounts")
    assert listed.status_code == 200
    assert [a["id"] for a in listed.json()] == [created["id"]]


async def test_account_type_must_be_valid(client: AsyncClient) -> None:
    await client.post("/api/v1/setup", json=SETUP_PAYLOAD)
    resp = await client.post(
        "/api/v1/accounts",
        json={
            "name": "Bad",
            "type": "bitcoin_wallet",
            "balance_cents": 0,
            "color": "#336699",
            "icon": "bank",
        },
        headers=_csrf_headers(client),
    )
    assert resp.status_code == 422


async def test_get_account_by_id(client: AsyncClient) -> None:
    await client.post("/api/v1/setup", json=SETUP_PAYLOAD)
    created = await _create_account(client)
    resp = await client.get(f"/api/v1/accounts/{created['id']}")
    assert resp.status_code == 200
    assert resp.json()["id"] == created["id"]


async def test_get_account_not_found(client: AsyncClient) -> None:
    await client.post("/api/v1/setup", json=SETUP_PAYLOAD)
    resp = await client.get("/api/v1/accounts/00000000-0000-0000-0000-000000000000")
    assert resp.status_code == 404


async def test_update_account(client: AsyncClient) -> None:
    await client.post("/api/v1/setup", json=SETUP_PAYLOAD)
    created = await _create_account(client)
    resp = await client.patch(
        f"/api/v1/accounts/{created['id']}",
        json={"name": "Renamed", "balance_cents": 5000},
        headers=_csrf_headers(client),
    )
    assert resp.status_code == 200
    assert resp.json()["name"] == "Renamed"
    assert resp.json()["balance_cents"] == 5000
    # Untouched fields survive a partial update.
    assert resp.json()["type"] == "checking"


async def test_archive_account_excludes_from_default_list(client: AsyncClient) -> None:
    await client.post("/api/v1/setup", json=SETUP_PAYLOAD)
    created = await _create_account(client)

    archive_resp = await client.post(
        f"/api/v1/accounts/{created['id']}/archive", headers=_csrf_headers(client)
    )
    assert archive_resp.status_code == 200
    assert archive_resp.json()["archived"] is True

    default_list = await client.get("/api/v1/accounts")
    assert default_list.json() == []

    with_archived = await client.get("/api/v1/accounts?include_archived=true")
    assert len(with_archived.json()) == 1
