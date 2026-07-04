from typing import Any

from httpx import AsyncClient

from tests.conftest import SETUP_PAYLOAD

DEFAULT_MAPPING = {"date": "Date", "description": "Description", "amount": "Amount"}


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


async def _paste_upload(client: AsyncClient, text: str) -> dict[str, Any]:
    resp = await client.post(
        "/api/v1/imports/paste", json={"text": text}, headers=_csrf_headers(client)
    )
    assert resp.status_code == 200, resp.text
    result: dict[str, Any] = resp.json()
    return result


async def test_exact_duplicate_flagged_and_skipped_by_default(client: AsyncClient) -> None:
    await client.post("/api/v1/setup", json=SETUP_PAYLOAD)
    account_id = await _create_account(client)
    text = "Date,Description,Amount\n01/15/2026,Grocery Store,-42.50\n"

    upload1 = await _paste_upload(client, text)
    commit1 = await client.post(
        f"/api/v1/imports/{upload1['import_session_id']}/commit",
        json={"column_mapping": DEFAULT_MAPPING, "date_format": "MDY", "account_id": account_id},
        headers=_csrf_headers(client),
    )
    assert commit1.json()["imported_count"] == 1

    # Same text pasted again -- a fresh session, but the same real-world
    # transaction -- must be flagged exact and skipped by default.
    upload2 = await _paste_upload(client, text)
    preview2 = await client.post(
        f"/api/v1/imports/{upload2['import_session_id']}/preview",
        json={"column_mapping": DEFAULT_MAPPING, "date_format": "MDY", "account_id": account_id},
    )
    preview_body = preview2.json()
    assert preview_body["exact_duplicate_count"] == 1
    assert preview_body["rows"][0]["will_import"] is False

    commit2 = await client.post(
        f"/api/v1/imports/{upload2['import_session_id']}/commit",
        json={"column_mapping": DEFAULT_MAPPING, "date_format": "MDY", "account_id": account_id},
        headers=_csrf_headers(client),
    )
    commit2_body = commit2.json()
    assert commit2_body["imported_count"] == 0
    assert commit2_body["skipped_dupes"] == 1


async def test_override_includes_exact_duplicate_anyway(client: AsyncClient) -> None:
    await client.post("/api/v1/setup", json=SETUP_PAYLOAD)
    account_id = await _create_account(client)
    text = "Date,Description,Amount\n01/15/2026,Grocery Store,-42.50\n"

    upload1 = await _paste_upload(client, text)
    await client.post(
        f"/api/v1/imports/{upload1['import_session_id']}/commit",
        json={"column_mapping": DEFAULT_MAPPING, "date_format": "MDY", "account_id": account_id},
        headers=_csrf_headers(client),
    )

    upload2 = await _paste_upload(client, text)
    commit2 = await client.post(
        f"/api/v1/imports/{upload2['import_session_id']}/commit",
        json={
            "column_mapping": DEFAULT_MAPPING,
            "date_format": "MDY",
            "account_id": account_id,
            "overrides": {"0": True},
        },
        headers=_csrf_headers(client),
    )
    commit2_body = commit2.json()
    assert commit2_body["imported_count"] == 1
    assert commit2_body["skipped_dupes"] == 0


async def test_fuzzy_duplicate_flagged_but_included_by_default(client: AsyncClient) -> None:
    await client.post("/api/v1/setup", json=SETUP_PAYLOAD)
    account_id = await _create_account(client)

    await client.post(
        "/api/v1/transactions",
        json={
            "account_id": account_id,
            "date": "2026-01-15",
            "amount_cents": -4250,
            "description": "Whole Foods Market #123",
        },
        headers=_csrf_headers(client),
    )

    # Same date+amount, similar-but-not-identical description -- should
    # fuzzy-flag for review (a different dedupe_hash than the exact one).
    text = "Date,Description,Amount\n01/15/2026,Whole Foods Mkt #123,-42.50\n"
    upload = await _paste_upload(client, text)
    preview = await client.post(
        f"/api/v1/imports/{upload['import_session_id']}/preview",
        json={"column_mapping": DEFAULT_MAPPING, "date_format": "MDY", "account_id": account_id},
    )
    body = preview.json()
    assert body["fuzzy_duplicate_count"] == 1
    assert body["exact_duplicate_count"] == 0
    assert body["rows"][0]["duplicate"] == "fuzzy"
    # Fuzzy is advisory only -- included by default, not skipped.
    assert body["rows"][0]["will_import"] is True


async def test_dissimilar_description_same_date_amount_not_flagged(client: AsyncClient) -> None:
    await client.post("/api/v1/setup", json=SETUP_PAYLOAD)
    account_id = await _create_account(client)

    await client.post(
        "/api/v1/transactions",
        json={
            "account_id": account_id,
            "date": "2026-01-15",
            "amount_cents": -4250,
            "description": "Whole Foods Market",
        },
        headers=_csrf_headers(client),
    )

    text = "Date,Description,Amount\n01/15/2026,Amazon Web Services,-42.50\n"
    upload = await _paste_upload(client, text)
    preview = await client.post(
        f"/api/v1/imports/{upload['import_session_id']}/preview",
        json={"column_mapping": DEFAULT_MAPPING, "date_format": "MDY", "account_id": account_id},
    )
    body = preview.json()
    assert body["fuzzy_duplicate_count"] == 0
    assert body["rows"][0]["duplicate"] is None


async def test_within_batch_duplicate_rows_flagged_from_second_occurrence(
    client: AsyncClient,
) -> None:
    await client.post("/api/v1/setup", json=SETUP_PAYLOAD)
    account_id = await _create_account(client)

    text = (
        "Date,Description,Amount\n01/15/2026,Coffee Shop,-4.50\n01/15/2026,Coffee Shop,-4.50\n"
    )
    upload = await _paste_upload(client, text)
    preview = await client.post(
        f"/api/v1/imports/{upload['import_session_id']}/preview",
        json={"column_mapping": DEFAULT_MAPPING, "date_format": "MDY", "account_id": account_id},
    )
    rows = preview.json()["rows"]
    assert rows[0]["duplicate"] is None
    assert rows[1]["duplicate"] == "exact"
