from pathlib import Path
from typing import Any

from httpx import AsyncClient
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from tests.conftest import SETUP_PAYLOAD, apply_session_cookies, seed_household

settings = get_settings()

_FIXTURE_DIR = Path(__file__).parent / "fixtures"


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


async def test_oversized_file_rejected(client: AsyncClient) -> None:
    await client.post("/api/v1/setup", json=SETUP_PAYLOAD)
    oversized = b"a" * (settings.import_max_file_bytes + 1)
    resp = await client.post(
        "/api/v1/imports/upload",
        files={"file": ("big.csv", oversized, "text/csv")},
        headers=_csrf_headers(client),
    )
    assert resp.status_code == 413


async def test_binary_content_rejected_even_with_csv_extension(client: AsyncClient) -> None:
    await client.post("/api/v1/setup", json=SETUP_PAYLOAD)
    binary_junk = bytes(range(256)) * 4
    resp = await client.post(
        "/api/v1/imports/upload",
        files={"file": ("totally-a-csv.csv", binary_junk, "text/csv")},
        headers=_csrf_headers(client),
    )
    assert resp.status_code == 400


async def test_too_many_rows_rejected(client: AsyncClient) -> None:
    await client.post("/api/v1/setup", json=SETUP_PAYLOAD)
    lines = ["Date,Description,Amount"]
    lines.extend(f"01/15/2026,Row {i},-1.00" for i in range(settings.import_max_rows + 1))
    content = "\n".join(lines).encode()
    resp = await client.post(
        "/api/v1/imports/upload",
        files={"file": ("huge.csv", content, "text/csv")},
        headers=_csrf_headers(client),
    )
    assert resp.status_code == 400


async def test_upload_auto_detects_mapping_and_date_format(client: AsyncClient) -> None:
    await client.post("/api/v1/setup", json=SETUP_PAYLOAD)
    content = (_FIXTURE_DIR / "chase_sample.csv").read_bytes()
    resp = await client.post(
        "/api/v1/imports/upload",
        files={"file": ("chase_sample.csv", content, "text/csv")},
        headers=_csrf_headers(client),
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["row_count"] == 6
    assert body["suggested_mapping"] == {
        "date": "Transaction Date",
        "description": "Description",
        "amount": "Amount",
        "dedupe_description": None,
    }
    assert body["date_format_suggestion"] == "MDY"
    assert body["date_format_ambiguous"] is False
    assert body["import_session_id"]


async def test_full_csv_import_flow_upload_preview_commit(client: AsyncClient) -> None:
    await client.post("/api/v1/setup", json=SETUP_PAYLOAD)
    account_id = await _create_account(client)
    content = (_FIXTURE_DIR / "chase_sample.csv").read_bytes()

    upload_resp = await client.post(
        "/api/v1/imports/upload",
        files={"file": ("chase_sample.csv", content, "text/csv")},
        headers=_csrf_headers(client),
    )
    assert upload_resp.status_code == 200
    upload_body = upload_resp.json()
    session_id = upload_body["import_session_id"]
    mapping = upload_body["suggested_mapping"]

    preview_resp = await client.post(
        f"/api/v1/imports/{session_id}/preview",
        json={"column_mapping": mapping, "date_format": "MDY", "account_id": account_id},
    )
    assert preview_resp.status_code == 200, preview_resp.text
    preview_body = preview_resp.json()
    assert preview_body["valid_count"] == 6
    assert preview_body["error_count"] == 0
    assert preview_body["exact_duplicate_count"] == 0
    assert all(row["will_import"] for row in preview_body["rows"])

    commit_resp = await client.post(
        f"/api/v1/imports/{session_id}/commit",
        json={"column_mapping": mapping, "date_format": "MDY", "account_id": account_id},
        headers=_csrf_headers(client),
    )
    assert commit_resp.status_code == 200, commit_resp.text
    batch = commit_resp.json()
    assert batch["row_count"] == 6
    assert batch["imported_count"] == 6
    assert batch["skipped_dupes"] == 0
    assert batch["undoable"] is True

    transactions_resp = await client.get("/api/v1/transactions?limit=100")
    items: list[dict[str, Any]] = transactions_resp.json()["items"]
    assert len(items) == 6
    assert {i["source"] for i in items} == {"csv"}


async def test_reimporting_same_file_yields_zero_new_rows(client: AsyncClient) -> None:
    await client.post("/api/v1/setup", json=SETUP_PAYLOAD)
    account_id = await _create_account(client)
    content = (_FIXTURE_DIR / "chase_sample.csv").read_bytes()

    async def _upload_preview_commit() -> dict[str, Any]:
        upload_resp = await client.post(
            "/api/v1/imports/upload",
            files={"file": ("chase_sample.csv", content, "text/csv")},
            headers=_csrf_headers(client),
        )
        body = upload_resp.json()
        commit_resp = await client.post(
            f"/api/v1/imports/{body['import_session_id']}/commit",
            json={
                "column_mapping": body["suggested_mapping"],
                "date_format": "MDY",
                "account_id": account_id,
            },
            headers=_csrf_headers(client),
        )
        result: dict[str, Any] = commit_resp.json()
        return result

    first = await _upload_preview_commit()
    assert first["imported_count"] == 6

    second = await _upload_preview_commit()
    assert second["imported_count"] == 0
    assert second["skipped_dupes"] == 6

    transactions_resp = await client.get("/api/v1/transactions?limit=100")
    assert len(transactions_resp.json()["items"]) == 6


async def test_cross_household_session_id_rejected(
    client: AsyncClient, db_session: AsyncSession, fake_redis: Redis
) -> None:
    _, _, _, session_a = await seed_household(
        db_session, fake_redis, household_name="Household A", owner_email="importa@example.com"
    )
    _, _, _, session_b = await seed_household(
        db_session, fake_redis, household_name="Household B", owner_email="importb@example.com"
    )

    apply_session_cookies(client, session_a)
    content = (_FIXTURE_DIR / "chase_sample.csv").read_bytes()
    upload_resp = await client.post(
        "/api/v1/imports/upload",
        files={"file": ("chase_sample.csv", content, "text/csv")},
        headers={"X-CSRF-Token": session_a.csrf_token},
    )
    session_id = upload_resp.json()["import_session_id"]

    apply_session_cookies(client, session_b)
    preview_resp = await client.post(
        f"/api/v1/imports/{session_id}/preview",
        json={
            "column_mapping": {
                "date": "Transaction Date",
                "description": "Description",
                "amount": "Amount",
            },
            "date_format": "MDY",
            "account_id": "00000000-0000-0000-0000-000000000000",
        },
    )
    assert preview_resp.status_code == 404


async def test_saved_profile_auto_applies_mapping_on_next_upload(client: AsyncClient) -> None:
    await client.post("/api/v1/setup", json=SETUP_PAYLOAD)
    content = (_FIXTURE_DIR / "chase_sample.csv").read_bytes()

    profile_resp = await client.post(
        "/api/v1/import-profiles",
        json={
            "name": "Chase Checking",
            "column_mapping": {
                "date": "Transaction Date",
                "description": "Description",
                "amount": "Amount",
            },
            "date_format": "MDY",
        },
        headers=_csrf_headers(client),
    )
    assert profile_resp.status_code == 201
    profile_id = profile_resp.json()["id"]

    upload_resp = await client.post(
        "/api/v1/imports/upload",
        files={"file": ("chase_sample.csv", content, "text/csv")},
        data={"profile_id": profile_id},
        headers=_csrf_headers(client),
    )
    assert upload_resp.status_code == 200
    body = upload_resp.json()
    assert body["suggested_mapping"] == {
        "date": "Transaction Date",
        "description": "Description",
        "amount": "Amount",
        "dedupe_description": None,
    }
    assert body["date_format_suggestion"] == "MDY"
    assert body["date_format_ambiguous"] is False
