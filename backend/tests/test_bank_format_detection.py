from pathlib import Path
from typing import Any

from httpx import AsyncClient

from tests.conftest import SETUP_PAYLOAD

_FIXTURE_DIR = Path(__file__).parent / "fixtures"


def _csrf_headers(client: AsyncClient) -> dict[str, str]:
    token = client.cookies.get("tally_csrf")
    assert token is not None
    return {"X-CSRF-Token": token}


async def _create_account(client: AsyncClient, **overrides: Any) -> dict[str, Any]:
    payload = {
        "name": "Wells Fargo Visa",
        "type": "credit_card",
        "balance_cents": 0,
        "color": "#CC2200",
        "icon": "card",
        **overrides,
    }
    resp = await client.post("/api/v1/accounts", json=payload, headers=_csrf_headers(client))
    assert resp.status_code == 201, resp.text
    result: dict[str, Any] = resp.json()
    return result


async def _upload_wells_fargo(client: AsyncClient) -> dict[str, Any]:
    content = (_FIXTURE_DIR / "wells_fargo_sample.csv").read_bytes()
    resp = await client.post(
        "/api/v1/imports/upload",
        files={"file": ("wells_fargo_sample.csv", content, "text/csv")},
        headers=_csrf_headers(client),
    )
    assert resp.status_code == 200, resp.text
    body: dict[str, Any] = resp.json()
    return body


async def test_upload_auto_detects_wells_fargo_format_and_skips_mapping(
    client: AsyncClient,
) -> None:
    await client.post("/api/v1/setup", json=SETUP_PAYLOAD)
    body = await _upload_wells_fargo(client)

    assert body["skip_mapping_step"] is True
    assert body["detected_bank_format"] == "Wells Fargo Credit Card"
    assert body["suggested_mapping"] == {
        "date": "Transaction Date",
        "description": "Description",
        "amount": "Amount",
        "dedupe_description": "Raw Merchant Name",
    }
    assert body["date_format_suggestion"] == "MDY"
    assert body["date_format_ambiguous"] is False


async def test_account_auto_suggested_from_card_last_four(client: AsyncClient) -> None:
    await client.post("/api/v1/setup", json=SETUP_PAYLOAD)
    account = await _create_account(client, last_four="1234")

    body = await _upload_wells_fargo(client)
    assert body["suggested_account_id"] == account["id"]


async def test_no_account_suggested_when_no_last_four_matches(client: AsyncClient) -> None:
    await client.post("/api/v1/setup", json=SETUP_PAYLOAD)
    await _create_account(client, last_four="9999")

    body = await _upload_wells_fargo(client)
    assert body["suggested_account_id"] is None


async def test_interest_charge_row_categorized_as_fees(client: AsyncClient) -> None:
    await client.post("/api/v1/setup", json=SETUP_PAYLOAD)
    account = await _create_account(client, last_four="1234")
    upload = await _upload_wells_fargo(client)

    preview_resp = await client.post(
        f"/api/v1/imports/{upload['import_session_id']}/preview",
        json={
            "column_mapping": upload["suggested_mapping"],
            "date_format": "MDY",
            "account_id": account["id"],
        },
    )
    assert preview_resp.status_code == 200, preview_resp.text
    rows = preview_resp.json()["rows"]

    interest_row = next(r for r in rows if r["description"] == "INTEREST CHARGE ON PURCHASES")
    assert interest_row["category_id"] is not None
    assert interest_row["error"] is None
    assert interest_row["amount_cents"] == 1234  # expense, positive, no sign transformation

    categories_resp = await client.get("/api/v1/categories")
    fees = next(c for c in categories_resp.json() if c["name"] == "Fees")
    assert interest_row["category_id"] == fees["id"]


async def test_payment_and_credit_rows_import_as_negative_without_card_attribution(
    client: AsyncClient,
) -> None:
    await client.post("/api/v1/setup", json=SETUP_PAYLOAD)
    account = await _create_account(client, last_four="1234")
    upload = await _upload_wells_fargo(client)

    commit_resp = await client.post(
        f"/api/v1/imports/{upload['import_session_id']}/commit",
        json={
            "column_mapping": upload["suggested_mapping"],
            "date_format": "MDY",
            "account_id": account["id"],
        },
        headers=_csrf_headers(client),
    )
    assert commit_resp.status_code == 200, commit_resp.text
    batch = commit_resp.json()
    assert batch["imported_count"] == 6
    assert batch["skipped_dupes"] == 0
    # Interest Charge -> Fees is the only guaranteed built-in-categorized row
    # in this fixture (Starbucks/Shell/Amazon patterns also match, so this
    # is a lower bound, not an exact count, to avoid over-coupling this test
    # to the full built-in merchant dictionary's contents).
    assert batch["auto_categorized_count"] >= 1

    transactions_resp = await client.get("/api/v1/transactions?limit=100")
    items = {i["description_raw"]: i for i in transactions_resp.json()["items"]}

    payment = items["ONLINE PAYMENT - THANK YOU"]
    assert payment["amount_cents"] == -50000

    credit = items["STATEMENT CREDIT"]
    assert credit["amount_cents"] == -2500

    refund = items["REFUNDED TO WELLS FARGO CARD"]
    assert refund["amount_cents"] == -1599


async def test_categorization_matches_raw_merchant_name_when_display_description_is_generic(
    client: AsyncClient,
) -> None:
    """SHELL SERVICE STATION's raw merchant name ("SHELL OIL ...") carries
    the identifying text the built-in Transport pattern needs; the display
    description alone doesn't contain it. Same story for the refund row --
    display description is generic Wells Fargo boilerplate ("REFUNDED TO
    WELLS FARGO CARD"), but its raw merchant name is "AMAZON.COM REFUND".
    Rule matching must consider both fields, not just the display one.
    """
    await client.post("/api/v1/setup", json=SETUP_PAYLOAD)
    account = await _create_account(client, last_four="1234")
    upload = await _upload_wells_fargo(client)

    preview_resp = await client.post(
        f"/api/v1/imports/{upload['import_session_id']}/preview",
        json={
            "column_mapping": upload["suggested_mapping"],
            "date_format": "MDY",
            "account_id": account["id"],
        },
    )
    assert preview_resp.status_code == 200, preview_resp.text
    rows = preview_resp.json()["rows"]

    shell_row = next(r for r in rows if r["description"] == "SHELL SERVICE STATION")
    assert shell_row["category_id"] is not None

    refund_row = next(r for r in rows if r["description"] == "REFUNDED TO WELLS FARGO CARD")
    assert refund_row["category_id"] is not None

    categories_resp = await client.get("/api/v1/categories")
    categories = {c["name"]: c["id"] for c in categories_resp.json()}
    assert shell_row["category_id"] == categories["Transport"]
    assert refund_row["category_id"] == categories["Misc"]


async def test_dedupe_hash_uses_raw_merchant_name_not_display_description(
    client: AsyncClient,
) -> None:
    """Two rows with the same Raw Merchant Name/date/amount but different
    Description text must still be flagged as an exact duplicate -- proving
    dedupe hashing reads dedupe_description (Raw Merchant Name), not the
    display description column, per the Wells Fargo mapping.
    """
    await client.post("/api/v1/setup", json=SETUP_PAYLOAD)
    account = await _create_account(client, last_four="1234")

    header = (
        "Transaction Date,Posted Date,Description,Amount,Card Last 4,Name on Card,Raw Merchant Name"
    )
    row_a = "02/01/2026,02/02/2026,COFFEE SHOP PURCHASE,5.00,1234,JANE DOE,SQ *COFFEE SHOP 999"
    row_b = (
        "02/01/2026,02/02/2026,A DIFFERENT LABEL ENTIRELY,5.00,1234,JANE DOE,SQ *COFFEE SHOP 999"
    )
    content = f"{header}\n{row_a}\n{row_b}\n".encode()

    upload_resp = await client.post(
        "/api/v1/imports/upload",
        files={"file": ("wf_dupe_check.csv", content, "text/csv")},
        headers=_csrf_headers(client),
    )
    assert upload_resp.status_code == 200, upload_resp.text
    upload = upload_resp.json()
    assert upload["skip_mapping_step"] is True

    preview_resp = await client.post(
        f"/api/v1/imports/{upload['import_session_id']}/preview",
        json={
            "column_mapping": upload["suggested_mapping"],
            "date_format": "MDY",
            "account_id": account["id"],
        },
    )
    rows = preview_resp.json()["rows"]
    assert rows[0]["duplicate"] is None
    assert rows[1]["duplicate"] == "exact"
