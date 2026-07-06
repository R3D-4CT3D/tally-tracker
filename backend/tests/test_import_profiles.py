from typing import Any

from httpx import AsyncClient

from tests.conftest import SETUP_PAYLOAD

MAPPING = {"date": "Date", "description": "Description", "amount": "Amount"}


def _csrf_headers(client: AsyncClient) -> dict[str, str]:
    token = client.cookies.get("tally_csrf")
    assert token is not None
    return {"X-CSRF-Token": token}


async def _create_profile(client: AsyncClient, **overrides: Any) -> dict[str, Any]:
    payload = {
        "name": "Chase Checking",
        "column_mapping": MAPPING,
        "date_format": "MDY",
        **overrides,
    }
    resp = await client.post("/api/v1/import-profiles", json=payload, headers=_csrf_headers(client))
    assert resp.status_code == 201, resp.text
    result: dict[str, Any] = resp.json()
    return result


async def test_create_and_list_import_profiles(client: AsyncClient) -> None:
    await client.post("/api/v1/setup", json=SETUP_PAYLOAD)
    created = await _create_profile(client)
    assert created["name"] == "Chase Checking"
    assert created["column_mapping"] == {**MAPPING, "dedupe_description": None}
    assert created["date_format"] == "MDY"

    listed = await client.get("/api/v1/import-profiles")
    assert listed.status_code == 200
    assert [p["id"] for p in listed.json()] == [created["id"]]


async def test_list_import_profiles_ordered_by_name(client: AsyncClient) -> None:
    await client.post("/api/v1/setup", json=SETUP_PAYLOAD)
    await _create_profile(client, name="Zeta Bank")
    await _create_profile(client, name="Alpha Bank")

    listed = await client.get("/api/v1/import-profiles")
    names = [p["name"] for p in listed.json()]
    assert names == ["Alpha Bank", "Zeta Bank"]


async def test_delete_import_profile(client: AsyncClient) -> None:
    await client.post("/api/v1/setup", json=SETUP_PAYLOAD)
    created = await _create_profile(client)

    delete_resp = await client.delete(
        f"/api/v1/import-profiles/{created['id']}", headers=_csrf_headers(client)
    )
    assert delete_resp.status_code == 204

    listed = await client.get("/api/v1/import-profiles")
    assert listed.json() == []


async def test_delete_nonexistent_import_profile_returns_404(client: AsyncClient) -> None:
    await client.post("/api/v1/setup", json=SETUP_PAYLOAD)
    resp = await client.delete(
        "/api/v1/import-profiles/00000000-0000-0000-0000-000000000000",
        headers=_csrf_headers(client),
    )
    assert resp.status_code == 404


async def test_upload_with_unknown_profile_id_returns_404(client: AsyncClient) -> None:
    await client.post("/api/v1/setup", json=SETUP_PAYLOAD)
    content = b"Date,Description,Amount\n01/15/2026,Coffee,-4.50\n"
    resp = await client.post(
        "/api/v1/imports/upload",
        files={"file": ("x.csv", content, "text/csv")},
        data={"profile_id": "00000000-0000-0000-0000-000000000000"},
        headers=_csrf_headers(client),
    )
    assert resp.status_code == 404
