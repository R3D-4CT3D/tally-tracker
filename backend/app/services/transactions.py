import base64
import hashlib
import uuid
from datetime import date as date_type

from sqlalchemy import select, tuple_
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.transaction import Transaction
from app.schemas.transactions import TransactionCreate, TransactionListParams, TransactionUpdate
from app.services.accounts import get_account
from app.services.categories import get_category

_DUPLICATE_MESSAGE = (
    "A transaction with the same account, date, amount, and description already exists"
)


class DuplicateTransactionError(Exception):
    """Raised when the (household_id, dedupe_hash) unique constraint is hit.

    Applies even to manual entry, not just future CSV import -- per spec §3's
    "trust through accuracy" principle, an accidental double-submission of an
    identical transaction is exactly the kind of thing that erodes trust in
    the tool, so it's worth catching here too, not just at import time.
    """


class InvalidReferenceError(Exception):
    """Raised when account_id/category_id doesn't resolve to a row in the
    caller's own household.

    Without this check, a household-scoped WHERE clause on the *new* row
    would still happily store someone else's account_id/category_id as a
    foreign key -- household_id on the transaction itself was always
    server-derived, but the referenced ids came straight from the client
    and were never verified to belong to that same household (a
    cross-household IDOR caught by security review after initial M2
    implementation).
    """


async def _validate_account_reference(
    db: AsyncSession, *, household_id: uuid.UUID, account_id: uuid.UUID
) -> None:
    account = await get_account(db, household_id=household_id, account_id=account_id)
    if account is None:
        raise InvalidReferenceError("Account not found")


async def _validate_category_reference(
    db: AsyncSession, *, household_id: uuid.UUID, category_id: uuid.UUID
) -> None:
    category = await get_category(db, household_id=household_id, category_id=category_id)
    if category is None:
        raise InvalidReferenceError("Category not found")


def normalize_description(text: str) -> str:
    return " ".join(text.strip().lower().split())


def compute_dedupe_hash(
    *,
    household_id: uuid.UUID,
    account_id: uuid.UUID,
    date: date_type,
    amount_cents: int,
    description: str,
) -> str:
    normalized = normalize_description(description)
    raw = f"{household_id}|{account_id}|{date.isoformat()}|{amount_cents}|{normalized}"
    return hashlib.sha256(raw.encode()).hexdigest()


def encode_cursor(date: date_type, transaction_id: uuid.UUID) -> str:
    raw = f"{date.isoformat()}|{transaction_id}"
    return base64.urlsafe_b64encode(raw.encode()).decode()


def decode_cursor(cursor: str) -> tuple[date_type, uuid.UUID]:
    raw = base64.urlsafe_b64decode(cursor.encode()).decode()
    date_str, id_str = raw.split("|", 1)
    return date_type.fromisoformat(date_str), uuid.UUID(id_str)


async def create_transaction(
    db: AsyncSession,
    *,
    household_id: uuid.UUID,
    created_by: uuid.UUID,
    payload: TransactionCreate,
) -> Transaction:
    await _validate_account_reference(db, household_id=household_id, account_id=payload.account_id)
    if payload.category_id is not None:
        await _validate_category_reference(
            db, household_id=household_id, category_id=payload.category_id
        )
    dedupe_hash = compute_dedupe_hash(
        household_id=household_id,
        account_id=payload.account_id,
        date=payload.date,
        amount_cents=payload.amount_cents,
        description=payload.description,
    )
    transaction = Transaction(
        household_id=household_id,
        account_id=payload.account_id,
        date=payload.date,
        amount_cents=payload.amount_cents,
        description_raw=payload.description,
        description_display=payload.description,
        category_id=payload.category_id,
        notes=payload.notes,
        source="manual",
        dedupe_hash=dedupe_hash,
        created_by=created_by,
    )
    db.add(transaction)
    try:
        await db.flush()
    except IntegrityError as exc:
        await db.rollback()
        raise DuplicateTransactionError(_DUPLICATE_MESSAGE) from exc
    return transaction


async def get_transaction(
    db: AsyncSession, *, household_id: uuid.UUID, transaction_id: uuid.UUID
) -> Transaction | None:
    stmt = select(Transaction).where(
        Transaction.household_id == household_id, Transaction.id == transaction_id
    )
    result = await db.execute(stmt)
    return result.scalar_one_or_none()


async def update_transaction(
    db: AsyncSession,
    *,
    household_id: uuid.UUID,
    transaction_id: uuid.UUID,
    payload: TransactionUpdate,
) -> Transaction | None:
    transaction = await get_transaction(
        db, household_id=household_id, transaction_id=transaction_id
    )
    if transaction is None:
        return None

    update_data = payload.model_dump(exclude_unset=True)

    if "account_id" in update_data:
        await _validate_account_reference(
            db, household_id=household_id, account_id=update_data["account_id"]
        )
    if "category_id" in update_data and update_data["category_id"] is not None:
        await _validate_category_reference(
            db, household_id=household_id, category_id=update_data["category_id"]
        )

    description = update_data.pop("description", None)
    if description is not None:
        transaction.description_raw = description
        transaction.description_display = description

    for key, value in update_data.items():
        setattr(transaction, key, value)

    dedupe_relevant_fields = {"account_id", "date", "amount_cents"}
    if dedupe_relevant_fields & update_data.keys() or description is not None:
        transaction.dedupe_hash = compute_dedupe_hash(
            household_id=household_id,
            account_id=transaction.account_id,
            date=transaction.date,
            amount_cents=transaction.amount_cents,
            description=transaction.description_raw,
        )

    try:
        await db.flush()
    except IntegrityError as exc:
        await db.rollback()
        raise DuplicateTransactionError(_DUPLICATE_MESSAGE) from exc
    return transaction


async def delete_transaction(
    db: AsyncSession, *, household_id: uuid.UUID, transaction_id: uuid.UUID
) -> bool:
    transaction = await get_transaction(
        db, household_id=household_id, transaction_id=transaction_id
    )
    if transaction is None:
        return False
    await db.delete(transaction)
    await db.flush()
    return True


async def list_transactions(
    db: AsyncSession, *, household_id: uuid.UUID, params: TransactionListParams
) -> tuple[list[Transaction], str | None]:
    stmt = select(Transaction).where(Transaction.household_id == household_id)

    if params.date_from is not None:
        stmt = stmt.where(Transaction.date >= params.date_from)
    if params.date_to is not None:
        stmt = stmt.where(Transaction.date <= params.date_to)
    if params.account_id is not None:
        stmt = stmt.where(Transaction.account_id == params.account_id)
    if params.uncategorized:
        stmt = stmt.where(Transaction.category_id.is_(None))
    elif params.category_id is not None:
        stmt = stmt.where(Transaction.category_id == params.category_id)
    if params.search:
        stmt = stmt.where(Transaction.description_display.ilike(f"%{params.search}%"))

    if params.cursor:
        cursor_date, cursor_id = decode_cursor(params.cursor)
        stmt = stmt.where(
            tuple_(Transaction.date, Transaction.id) < tuple_(cursor_date, cursor_id)  # type: ignore[arg-type]
        )

    # Keyset pagination: order matches the cursor comparison exactly (date
    # DESC, id DESC as tiebreaker) -- fetch one extra row to know whether
    # there's a next page without a separate COUNT query.
    stmt = stmt.order_by(Transaction.date.desc(), Transaction.id.desc()).limit(params.limit + 1)
    result = await db.execute(stmt)
    rows = list(result.scalars().all())

    next_cursor = None
    if len(rows) > params.limit:
        rows = rows[: params.limit]
        last = rows[-1]
        next_cursor = encode_cursor(last.date, last.id)

    return rows, next_cursor
