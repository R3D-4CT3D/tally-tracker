import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import CurrentUser, verify_csrf
from app.core.db import get_db
from app.schemas.accounts import AccountCreate, AccountOut, AccountUpdate
from app.services.accounts import (
    archive_account,
    create_account,
    get_account,
    list_accounts,
    update_account,
)

router = APIRouter(prefix="/accounts", tags=["accounts"])


@router.post(
    "",
    response_model=AccountOut,
    dependencies=[Depends(verify_csrf)],
    status_code=status.HTTP_201_CREATED,
)
async def create_account_route(
    payload: AccountCreate,
    current_user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> AccountOut:
    account = await create_account(
        db, household_id=uuid.UUID(current_user.household_id), payload=payload
    )
    await db.commit()
    return AccountOut.model_validate(account)


@router.get("", response_model=list[AccountOut])
async def list_accounts_route(
    current_user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
    include_archived: bool = False,
) -> list[AccountOut]:
    accounts = await list_accounts(
        db, household_id=uuid.UUID(current_user.household_id), include_archived=include_archived
    )
    return [AccountOut.model_validate(a) for a in accounts]


@router.get("/{account_id}", response_model=AccountOut)
async def get_account_route(
    account_id: uuid.UUID,
    current_user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> AccountOut:
    account = await get_account(
        db, household_id=uuid.UUID(current_user.household_id), account_id=account_id
    )
    if account is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Account not found")
    return AccountOut.model_validate(account)


@router.patch("/{account_id}", response_model=AccountOut, dependencies=[Depends(verify_csrf)])
async def update_account_route(
    account_id: uuid.UUID,
    payload: AccountUpdate,
    current_user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> AccountOut:
    account = await update_account(
        db,
        household_id=uuid.UUID(current_user.household_id),
        account_id=account_id,
        payload=payload,
    )
    if account is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Account not found")
    await db.commit()
    return AccountOut.model_validate(account)


@router.post(
    "/{account_id}/archive",
    response_model=AccountOut,
    dependencies=[Depends(verify_csrf)],
)
async def archive_account_route(
    account_id: uuid.UUID,
    current_user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> AccountOut:
    account = await archive_account(
        db, household_id=uuid.UUID(current_user.household_id), account_id=account_id
    )
    if account is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Account not found")
    await db.commit()
    return AccountOut.model_validate(account)
