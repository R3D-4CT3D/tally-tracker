import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.account import Account
from app.schemas.accounts import AccountCreate, AccountUpdate


async def create_account(
    db: AsyncSession, *, household_id: uuid.UUID, payload: AccountCreate
) -> Account:
    account = Account(household_id=household_id, **payload.model_dump())
    db.add(account)
    await db.flush()
    return account


async def list_accounts(
    db: AsyncSession, *, household_id: uuid.UUID, include_archived: bool = False
) -> list[Account]:
    stmt = select(Account).where(Account.household_id == household_id)
    if not include_archived:
        stmt = stmt.where(Account.archived.is_(False))
    stmt = stmt.order_by(Account.created_at)
    result = await db.execute(stmt)
    return list(result.scalars().all())


async def get_account(
    db: AsyncSession, *, household_id: uuid.UUID, account_id: uuid.UUID
) -> Account | None:
    stmt = select(Account).where(Account.household_id == household_id, Account.id == account_id)
    result = await db.execute(stmt)
    return result.scalar_one_or_none()


async def update_account(
    db: AsyncSession, *, household_id: uuid.UUID, account_id: uuid.UUID, payload: AccountUpdate
) -> Account | None:
    account = await get_account(db, household_id=household_id, account_id=account_id)
    if account is None:
        return None
    for key, value in payload.model_dump(exclude_unset=True).items():
        setattr(account, key, value)
    await db.flush()
    return account


async def archive_account(
    db: AsyncSession, *, household_id: uuid.UUID, account_id: uuid.UUID
) -> Account | None:
    account = await get_account(db, household_id=household_id, account_id=account_id)
    if account is None:
        return None
    account.archived = True
    await db.flush()
    return account
