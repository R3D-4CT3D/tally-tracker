import uuid
from datetime import date as date_type
from datetime import timedelta

from dateutil.relativedelta import relativedelta
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.bill_payment import BillPayment
from app.schemas.bills import BillMarkPaidRequest
from app.schemas.transactions import TransactionCreate
from app.services.bills import BillValidationError, get_bill
from app.services.transactions import InvalidReferenceError, create_transaction, get_transaction


def compute_next_due_date(
    current_due_date: date_type, frequency: str, custom_interval_days: int | None
) -> date_type:
    """Always advances from the bill's own `next_due_date`, not from "today" --
    marking a bill paid early or late shouldn't shift its underlying cadence.
    `relativedelta` (not manual month arithmetic) correctly clamps
    day-of-month overflow, e.g. Jan 31 + 1 month -> Feb 28/29, rather than
    erroring or silently rolling to Mar 3.
    """
    if frequency == "monthly":
        return current_due_date + relativedelta(months=1)
    if frequency == "quarterly":
        return current_due_date + relativedelta(months=3)
    if frequency == "annual":
        return current_due_date + relativedelta(years=1)
    if frequency == "custom":
        if custom_interval_days is None:
            raise BillValidationError(
                "custom_interval_days is required when frequency is 'custom'"
            )
        return current_due_date + timedelta(days=custom_interval_days)
    raise BillValidationError(f"Unknown frequency: {frequency!r}")


async def mark_bill_paid(
    db: AsyncSession,
    *,
    household_id: uuid.UUID,
    bill_id: uuid.UUID,
    created_by: uuid.UUID,
    payload: BillMarkPaidRequest,
) -> BillPayment | None:
    bill = await get_bill(db, household_id=household_id, bill_id=bill_id)
    if bill is None:
        return None

    if payload.transaction_id is not None:
        # Link path: the linked transaction is the source of truth for
        # date/amount -- separately-supplied quick-create fields are ignored
        # rather than trusted, closing the same cross-household IDOR class
        # transactions.py's own _validate_*_reference helpers close.
        transaction = await get_transaction(
            db, household_id=household_id, transaction_id=payload.transaction_id
        )
        if transaction is None:
            raise InvalidReferenceError("Transaction not found")
    else:
        if payload.account_id is None or payload.amount_cents is None or payload.date is None:
            raise BillValidationError(
                "account_id, amount_cents, and date are required for quick-create"
                " when no transaction_id is supplied"
            )
        transaction = await create_transaction(
            db,
            household_id=household_id,
            created_by=created_by,
            payload=TransactionCreate(
                account_id=payload.account_id,
                date=payload.date,
                amount_cents=payload.amount_cents,
                description=f"Bill payment: {bill.name}",
                category_id=payload.category_id or bill.category_id,
                notes=payload.notes,
            ),
        )

    payment = BillPayment(
        household_id=household_id,
        bill_id=bill.id,
        transaction_id=transaction.id,
        due_date=bill.next_due_date,
        paid_date=transaction.date,
        amount_cents=transaction.amount_cents,
        status="paid",
    )
    bill.next_due_date = compute_next_due_date(
        bill.next_due_date, bill.frequency, bill.custom_interval_days
    )
    db.add(payment)
    await db.flush()
    return payment


async def list_bill_payments(
    db: AsyncSession, *, household_id: uuid.UUID, bill_id: uuid.UUID
) -> list[BillPayment]:
    stmt = (
        select(BillPayment)
        .where(BillPayment.household_id == household_id, BillPayment.bill_id == bill_id)
        .order_by(BillPayment.due_date.desc())
    )
    result = await db.execute(stmt)
    return list(result.scalars().all())
