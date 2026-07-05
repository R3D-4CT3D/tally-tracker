import base64
import hashlib
import uuid
from datetime import date as date_type
from datetime import datetime
from typing import Any

from sqlalchemy import Select, func, select, tuple_
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.transaction import Transaction
from app.schemas.transactions import (
    TransactionCountParams,
    TransactionCreate,
    TransactionListParams,
    TransactionUpdate,
)
from app.services.accounts import get_account
from app.services.categories import get_category
from app.services.debts import adjust_debt_balance_for_transaction, get_debt

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


async def _validate_debt_reference(
    db: AsyncSession, *, household_id: uuid.UUID, debt_id: uuid.UUID
) -> None:
    debt = await get_debt(db, household_id=household_id, debt_id=debt_id)
    if debt is None:
        raise InvalidReferenceError("Debt not found")


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
    if payload.debt_id is not None:
        await _validate_debt_reference(db, household_id=household_id, debt_id=payload.debt_id)
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
        debt_id=payload.debt_id,
    )
    db.add(transaction)
    try:
        await db.flush()
    except IntegrityError as exc:
        await db.rollback()
        raise DuplicateTransactionError(_DUPLICATE_MESSAGE) from exc
    if payload.debt_id is not None:
        await adjust_debt_balance_for_transaction(
            db, household_id=household_id, debt_id=payload.debt_id, delta_cents=payload.amount_cents
        )
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
    if "debt_id" in update_data and update_data["debt_id"] is not None:
        await _validate_debt_reference(
            db, household_id=household_id, debt_id=update_data["debt_id"]
        )

    # Captured before mutation: reversing/reapplying the debt-balance
    # adjustment below needs the *old* debt_id/amount, which setattr()
    # overwrites in place.
    old_debt_id = transaction.debt_id
    old_amount_cents = transaction.amount_cents
    debt_adjustment_relevant = {"debt_id", "amount_cents"} & update_data.keys()

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

    if debt_adjustment_relevant:
        # Reverse-then-reapply (not a blind re-add) handles every case
        # uniformly: debt_id unset->set, set->unset, set->a different debt,
        # and amount_cents changed on the same debt.
        new_debt_id = transaction.debt_id
        new_amount_cents = transaction.amount_cents
        if old_debt_id is not None:
            await adjust_debt_balance_for_transaction(
                db, household_id=household_id, debt_id=old_debt_id, delta_cents=-old_amount_cents
            )
        if new_debt_id is not None:
            await adjust_debt_balance_for_transaction(
                db, household_id=household_id, debt_id=new_debt_id, delta_cents=new_amount_cents
            )

    return transaction


async def delete_transaction(
    db: AsyncSession, *, household_id: uuid.UUID, transaction_id: uuid.UUID
) -> bool:
    transaction = await get_transaction(
        db, household_id=household_id, transaction_id=transaction_id
    )
    if transaction is None:
        return False
    if transaction.debt_id is not None:
        # ondelete="SET NULL" on transactions.debt_id only fires if the
        # *debt* row is deleted, not the transaction -- deleting a
        # debt-linked transaction is a normal app-level delete, so the
        # balance adjustment must be reversed explicitly here first.
        await adjust_debt_balance_for_transaction(
            db,
            household_id=household_id,
            debt_id=transaction.debt_id,
            delta_cents=-transaction.amount_cents,
        )
    await db.delete(transaction)
    await db.flush()
    return True


def _apply_common_filters[SelectT: Select[Any]](
    stmt: SelectT,
    *,
    date_from: date_type | None,
    date_to: date_type | None,
    account_id: uuid.UUID | None,
    category_id: uuid.UUID | None,
    uncategorized: bool,
    debt_id: uuid.UUID | None,
    created_after: datetime | None,
    search: str | None,
) -> SelectT:
    """Shared between list_transactions and count_transactions so the two
    never drift out of sync with each other's filter semantics.
    """
    if date_from is not None:
        stmt = stmt.where(Transaction.date >= date_from)
    if date_to is not None:
        stmt = stmt.where(Transaction.date <= date_to)
    if account_id is not None:
        stmt = stmt.where(Transaction.account_id == account_id)
    if uncategorized:
        stmt = stmt.where(Transaction.category_id.is_(None))
    elif category_id is not None:
        stmt = stmt.where(Transaction.category_id == category_id)
    if debt_id is not None:
        stmt = stmt.where(Transaction.debt_id == debt_id)
    if created_after is not None:
        stmt = stmt.where(Transaction.created_at >= created_after)
    if search:
        stmt = stmt.where(Transaction.description_display.ilike(f"%{search}%"))
    return stmt


async def list_transactions(
    db: AsyncSession, *, household_id: uuid.UUID, params: TransactionListParams
) -> tuple[list[Transaction], str | None]:
    stmt = select(Transaction).where(Transaction.household_id == household_id)
    stmt = _apply_common_filters(
        stmt,
        date_from=params.date_from,
        date_to=params.date_to,
        account_id=params.account_id,
        category_id=params.category_id,
        uncategorized=params.uncategorized,
        debt_id=params.debt_id,
        created_after=params.created_after,
        search=params.search,
    )

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


async def count_transactions(
    db: AsyncSession, *, household_id: uuid.UUID, params: TransactionCountParams
) -> int:
    """A dedicated COUNT query rather than piggybacking a total on
    list_transactions's response -- that endpoint is hot/frequently-polled
    (the transactions page), and only the dashboard's "uncategorized count"
    widget (M5) needs a total.
    """
    stmt = select(func.count()).select_from(Transaction).where(
        Transaction.household_id == household_id
    )
    stmt = _apply_common_filters(
        stmt,
        date_from=params.date_from,
        date_to=params.date_to,
        account_id=params.account_id,
        category_id=params.category_id,
        uncategorized=params.uncategorized,
        debt_id=params.debt_id,
        created_after=params.created_after,
        search=params.search,
    )
    result = await db.execute(stmt)
    return result.scalar_one()
