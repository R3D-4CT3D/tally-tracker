import uuid
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.debt import Debt
from app.schemas.debts import DebtCreate, DebtUpdate


class InvalidDebtReferenceError(Exception):
    """Raised when a client-supplied debt_id doesn't resolve to a row in the
    caller's own household -- same IDOR-closing purpose as
    transactions.py's InvalidReferenceError, kept as its own type here since
    debts.py has no other reason to import from transactions.py (which
    already imports get_debt from this module for the reverse direction).
    """


async def create_debt(db: AsyncSession, *, household_id: uuid.UUID, payload: DebtCreate) -> Debt:
    debt = Debt(household_id=household_id, **payload.model_dump())
    db.add(debt)
    await db.flush()
    return debt


async def list_debts(
    db: AsyncSession, *, household_id: uuid.UUID, include_archived: bool = False
) -> list[Debt]:
    stmt = select(Debt).where(Debt.household_id == household_id)
    if not include_archived:
        stmt = stmt.where(Debt.archived.is_(False))
    stmt = stmt.order_by(Debt.created_at)
    result = await db.execute(stmt)
    return list(result.scalars().all())


async def get_debt(db: AsyncSession, *, household_id: uuid.UUID, debt_id: uuid.UUID) -> Debt | None:
    stmt = select(Debt).where(Debt.household_id == household_id, Debt.id == debt_id)
    result = await db.execute(stmt)
    return result.scalar_one_or_none()


async def update_debt(
    db: AsyncSession, *, household_id: uuid.UUID, debt_id: uuid.UUID, payload: DebtUpdate
) -> Debt | None:
    debt = await get_debt(db, household_id=household_id, debt_id=debt_id)
    if debt is None:
        return None
    for key, value in payload.model_dump(exclude_unset=True).items():
        setattr(debt, key, value)
    await db.flush()
    return debt


async def archive_debt(
    db: AsyncSession, *, household_id: uuid.UUID, debt_id: uuid.UUID
) -> Debt | None:
    debt = await get_debt(db, household_id=household_id, debt_id=debt_id)
    if debt is None:
        return None
    # archived and paid_off_at are independent -- archiving a debt with a
    # nonzero balance is allowed (matches Account's archived semantics
    # exactly) and must not be conflated with "this debt is resolved."
    debt.archived = True
    await db.flush()
    return debt


def _maybe_toggle_paid_off(debt: Debt) -> None:
    """Symmetric, not a one-way ratchet: a debt's paid_off_at reflects
    current truth. If a later adjustment (e.g. deleting the transaction that
    paid it off, or a new charge) pushes the balance back above zero, clear
    paid_off_at rather than leaving a stale "paid off" timestamp.
    """
    if debt.current_balance_cents <= 0 and debt.paid_off_at is None:
        debt.paid_off_at = datetime.now(UTC)
    elif debt.current_balance_cents > 0 and debt.paid_off_at is not None:
        debt.paid_off_at = None


async def adjust_debt_balance_for_transaction(
    db: AsyncSession, *, household_id: uuid.UUID, debt_id: uuid.UUID, delta_cents: int
) -> None:
    """A debt-linked transaction's amount_cents is applied directly to
    current_balance_cents: a negative amount (a payment) reduces the
    balance, a positive amount (a new charge/refund) increases it. This
    function is the single place that sign convention lives -- callers in
    transactions.py never touch current_balance_cents directly.
    """
    debt = await get_debt(db, household_id=household_id, debt_id=debt_id)
    if debt is None:
        raise InvalidDebtReferenceError("Debt not found")
    debt.current_balance_cents += delta_cents
    _maybe_toggle_paid_off(debt)
    await db.flush()
