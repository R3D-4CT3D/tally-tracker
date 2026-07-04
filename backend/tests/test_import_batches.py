import uuid
from datetime import UTC, datetime, timedelta
from typing import Any

from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.import_batch import ImportBatch
from app.schemas.imports import ColumnMapping
from app.services.import_sessions import ImportSessionData
from app.services.imports import commit_import
from app.services.transactions import DuplicateTransactionError
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


async def test_commit_creates_batch_and_transactions_atomically(client: AsyncClient) -> None:
    await client.post("/api/v1/setup", json=SETUP_PAYLOAD)
    account_id = await _create_account(client)
    text = (
        "Date,Description,Amount\n"
        "01/15/2026,Coffee Shop,-4.50\n"
        "01/16/2026,Paycheck,1500.00\n"
        "01/17/2026,Groceries,-84.32\n"
    )
    upload = await _paste_upload(client, text)
    commit = await client.post(
        f"/api/v1/imports/{upload['import_session_id']}/commit",
        json={"column_mapping": DEFAULT_MAPPING, "date_format": "MDY", "account_id": account_id},
        headers=_csrf_headers(client),
    )
    assert commit.status_code == 200
    batch = commit.json()
    assert batch["row_count"] == 3
    assert batch["imported_count"] == 3

    batches_resp = await client.get("/api/v1/imports/batches")
    assert len(batches_resp.json()) == 1
    assert batches_resp.json()[0]["id"] == batch["id"]

    transactions_resp = await client.get("/api/v1/transactions?limit=100")
    items = transactions_resp.json()["items"]
    assert len(items) == 3
    assert all(i["source"] == "paste" for i in items)


async def test_undo_within_window_deletes_all_transactions_atomically(
    client: AsyncClient,
) -> None:
    await client.post("/api/v1/setup", json=SETUP_PAYLOAD)
    account_id = await _create_account(client)
    text = "Date,Description,Amount\n01/15/2026,Coffee Shop,-4.50\n01/16/2026,Paycheck,1500.00\n"
    upload = await _paste_upload(client, text)
    commit = await client.post(
        f"/api/v1/imports/{upload['import_session_id']}/commit",
        json={"column_mapping": DEFAULT_MAPPING, "date_format": "MDY", "account_id": account_id},
        headers=_csrf_headers(client),
    )
    batch_id = commit.json()["id"]
    assert commit.json()["undoable"] is True

    undo_resp = await client.delete(
        f"/api/v1/imports/batches/{batch_id}", headers=_csrf_headers(client)
    )
    assert undo_resp.status_code == 204

    transactions_resp = await client.get("/api/v1/transactions?limit=100")
    assert transactions_resp.json()["items"] == []

    batches_resp = await client.get("/api/v1/imports/batches")
    assert batches_resp.json() == []


async def test_undo_after_window_is_rejected(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    await client.post("/api/v1/setup", json=SETUP_PAYLOAD)
    account_id = await _create_account(client)
    text = "Date,Description,Amount\n01/15/2026,Coffee Shop,-4.50\n"
    upload = await _paste_upload(client, text)
    commit = await client.post(
        f"/api/v1/imports/{upload['import_session_id']}/commit",
        json={"column_mapping": DEFAULT_MAPPING, "date_format": "MDY", "account_id": account_id},
        headers=_csrf_headers(client),
    )
    batch_id = commit.json()["id"]

    # Backdate the batch directly in the test DB rather than adding a
    # time-mocking dependency -- simplest way to exercise the 24h window
    # boundary deterministically.
    stmt = select(ImportBatch).where(ImportBatch.id == uuid.UUID(batch_id))
    result = await db_session.execute(stmt)
    batch = result.scalar_one()
    batch.created_at = datetime.now(UTC) - timedelta(hours=25)
    await db_session.commit()

    undo_resp = await client.delete(
        f"/api/v1/imports/batches/{batch_id}", headers=_csrf_headers(client)
    )
    assert undo_resp.status_code == 400

    transactions_resp = await client.get("/api/v1/transactions?limit=100")
    assert len(transactions_resp.json()["items"]) == 1


async def test_batches_list_reports_undoable_false_past_window(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    await client.post("/api/v1/setup", json=SETUP_PAYLOAD)
    account_id = await _create_account(client)
    text = "Date,Description,Amount\n01/15/2026,Coffee Shop,-4.50\n"
    upload = await _paste_upload(client, text)
    commit = await client.post(
        f"/api/v1/imports/{upload['import_session_id']}/commit",
        json={"column_mapping": DEFAULT_MAPPING, "date_format": "MDY", "account_id": account_id},
        headers=_csrf_headers(client),
    )
    batch_id = commit.json()["id"]

    stmt = select(ImportBatch).where(ImportBatch.id == uuid.UUID(batch_id))
    result = await db_session.execute(stmt)
    batch = result.scalar_one()
    batch.created_at = datetime.now(UTC) - timedelta(hours=25)
    await db_session.commit()

    batches_resp = await client.get("/api/v1/imports/batches")
    assert batches_resp.json()[0]["undoable"] is False


async def test_undo_nonexistent_batch_returns_404(client: AsyncClient) -> None:
    await client.post("/api/v1/setup", json=SETUP_PAYLOAD)
    resp = await client.delete(
        "/api/v1/imports/batches/00000000-0000-0000-0000-000000000000",
        headers=_csrf_headers(client),
    )
    assert resp.status_code == 404


async def test_partial_failure_rolls_back_whole_batch(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    """A dedupe_hash collision during the final flush (a genuine concurrent-
    import race between two requests -- not something reachable through
    this request's own duplicate detection, which is deliberately
    disambiguated via hash-salting so a forced-include override never
    collides; see test_imports_dedupe.py) must roll back the whole batch,
    not leave a partially-imported one. Simulated by monkeypatching
    `db.flush` to fail on its second call (the first flush persists the
    batch row itself and must succeed) -- the only deterministic way to
    exercise this specific race without real concurrency.
    """
    await client.post("/api/v1/setup", json=SETUP_PAYLOAD)
    me = (await client.get("/api/v1/auth/me")).json()
    household_id = uuid.UUID(me["household_id"])
    user_id = uuid.UUID(me["user_id"])
    account_id = uuid.UUID(await _create_account(client))

    session = ImportSessionData(
        session_id="test-session",
        household_id=str(household_id),
        filename="race.csv",
        source="csv",
        header=["Date", "Description", "Amount"],
        rows=[["01/19/2026", "First Good Row", "-10.00"]],
    )

    original_flush = db_session.flush
    call_count = 0

    async def _flush_fail_on_second_call() -> None:
        nonlocal call_count
        call_count += 1
        if call_count == 2:
            raise IntegrityError("mocked collision", {}, Exception("dedupe_hash"))
        await original_flush()

    db_session.flush = _flush_fail_on_second_call  # type: ignore[method-assign,assignment]

    raised = False
    try:
        await commit_import(
            db_session,
            household_id=household_id,
            user_id=user_id,
            session=session,
            mapping=ColumnMapping(date="Date", description="Description", amount="Amount"),
            date_format="MDY",
            account_id=account_id,
            overrides={},
            source_profile_id=None,
            fuzzy_threshold=0.6,
            regex_timeout=0.05,
        )
    except DuplicateTransactionError:
        raised = True
    finally:
        db_session.flush = original_flush  # type: ignore[method-assign]

    assert raised is True

    batches_after = await client.get("/api/v1/imports/batches")
    assert batches_after.json() == []
    transactions_after = await client.get("/api/v1/transactions?limit=100")
    assert transactions_after.json()["items"] == []
