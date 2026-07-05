import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.bill import Bill
from app.schemas.bills import BillCreate, BillUpdate
from app.services.accounts import get_account
from app.services.categories import get_category
from app.services.transactions import InvalidReferenceError


class BillValidationError(Exception):
    """Invalid bill definition -- currently only the custom-frequency/
    custom_interval_days pairing, enforced here rather than a DB CHECK
    constraint per the codebase's "no CHECK constraints, validity enforced
    in the service/Pydantic layer" convention.
    """


def _validate_custom_interval(frequency: str, custom_interval_days: int | None) -> None:
    if frequency == "custom" and custom_interval_days is None:
        raise BillValidationError("custom_interval_days is required when frequency is 'custom'")


async def _validate_references(
    db: AsyncSession,
    *,
    household_id: uuid.UUID,
    account_id: uuid.UUID | None,
    category_id: uuid.UUID | None,
) -> None:
    if account_id is not None:
        account = await get_account(db, household_id=household_id, account_id=account_id)
        if account is None:
            raise InvalidReferenceError("Account not found")
    if category_id is not None:
        category = await get_category(db, household_id=household_id, category_id=category_id)
        if category is None:
            raise InvalidReferenceError("Category not found")


async def create_bill(db: AsyncSession, *, household_id: uuid.UUID, payload: BillCreate) -> Bill:
    _validate_custom_interval(payload.frequency, payload.custom_interval_days)
    await _validate_references(
        db,
        household_id=household_id,
        account_id=payload.account_id,
        category_id=payload.category_id,
    )
    bill = Bill(household_id=household_id, **payload.model_dump())
    db.add(bill)
    await db.flush()
    return bill


async def list_bills(
    db: AsyncSession, *, household_id: uuid.UUID, include_archived: bool = False
) -> list[Bill]:
    stmt = select(Bill).where(Bill.household_id == household_id)
    if not include_archived:
        stmt = stmt.where(Bill.archived.is_(False))
    stmt = stmt.order_by(Bill.next_due_date)
    result = await db.execute(stmt)
    return list(result.scalars().all())


async def get_bill(db: AsyncSession, *, household_id: uuid.UUID, bill_id: uuid.UUID) -> Bill | None:
    stmt = select(Bill).where(Bill.household_id == household_id, Bill.id == bill_id)
    result = await db.execute(stmt)
    return result.scalar_one_or_none()


async def update_bill(
    db: AsyncSession, *, household_id: uuid.UUID, bill_id: uuid.UUID, payload: BillUpdate
) -> Bill | None:
    bill = await get_bill(db, household_id=household_id, bill_id=bill_id)
    if bill is None:
        return None

    update_data = payload.model_dump(exclude_unset=True)

    _validate_custom_interval(
        update_data.get("frequency", bill.frequency),
        update_data.get("custom_interval_days", bill.custom_interval_days),
    )
    if "account_id" in update_data or "category_id" in update_data:
        await _validate_references(
            db,
            household_id=household_id,
            account_id=update_data.get("account_id", bill.account_id),
            category_id=update_data.get("category_id", bill.category_id),
        )

    for key, value in update_data.items():
        setattr(bill, key, value)
    await db.flush()
    return bill


async def archive_bill(
    db: AsyncSession, *, household_id: uuid.UUID, bill_id: uuid.UUID
) -> Bill | None:
    bill = await get_bill(db, household_id=household_id, bill_id=bill_id)
    if bill is None:
        return None
    bill.archived = True
    await db.flush()
    return bill
