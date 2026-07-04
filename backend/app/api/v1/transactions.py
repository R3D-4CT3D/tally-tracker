import uuid
from datetime import date as date_type
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import CurrentUser, verify_csrf
from app.core.db import get_db
from app.schemas.transactions import (
    TransactionCreate,
    TransactionListParams,
    TransactionListResponse,
    TransactionOut,
    TransactionUpdate,
)
from app.services.transactions import (
    DuplicateTransactionError,
    create_transaction,
    delete_transaction,
    get_transaction,
    list_transactions,
    update_transaction,
)

router = APIRouter(prefix="/transactions", tags=["transactions"])


@router.post(
    "",
    response_model=TransactionOut,
    dependencies=[Depends(verify_csrf)],
    status_code=status.HTTP_201_CREATED,
)
async def create_transaction_route(
    payload: TransactionCreate,
    current_user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> TransactionOut:
    try:
        transaction = await create_transaction(
            db,
            household_id=uuid.UUID(current_user.household_id),
            created_by=uuid.UUID(current_user.user_id),
            payload=payload,
        )
    except DuplicateTransactionError as exc:
        raise HTTPException(status.HTTP_409_CONFLICT, str(exc)) from exc
    await db.commit()
    return TransactionOut.model_validate(transaction)


@router.get("", response_model=TransactionListResponse)
async def list_transactions_route(
    current_user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
    date_from: date_type | None = None,
    date_to: date_type | None = None,
    account_id: uuid.UUID | None = None,
    category_id: uuid.UUID | None = None,
    uncategorized: bool = False,
    search: str | None = Query(default=None, max_length=200),
    cursor: str | None = None,
    limit: int = Query(default=25, ge=1, le=100),
) -> TransactionListResponse:
    params = TransactionListParams(
        date_from=date_from,
        date_to=date_to,
        account_id=account_id,
        category_id=category_id,
        uncategorized=uncategorized,
        search=search,
        cursor=cursor,
        limit=limit,
    )
    rows, next_cursor = await list_transactions(
        db, household_id=uuid.UUID(current_user.household_id), params=params
    )
    return TransactionListResponse(
        items=[TransactionOut.model_validate(t) for t in rows], next_cursor=next_cursor
    )


@router.get("/{transaction_id}", response_model=TransactionOut)
async def get_transaction_route(
    transaction_id: uuid.UUID,
    current_user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> TransactionOut:
    transaction = await get_transaction(
        db, household_id=uuid.UUID(current_user.household_id), transaction_id=transaction_id
    )
    if transaction is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Transaction not found")
    return TransactionOut.model_validate(transaction)


@router.patch(
    "/{transaction_id}",
    response_model=TransactionOut,
    dependencies=[Depends(verify_csrf)],
)
async def update_transaction_route(
    transaction_id: uuid.UUID,
    payload: TransactionUpdate,
    current_user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> TransactionOut:
    try:
        transaction = await update_transaction(
            db,
            household_id=uuid.UUID(current_user.household_id),
            transaction_id=transaction_id,
            payload=payload,
        )
    except DuplicateTransactionError as exc:
        raise HTTPException(status.HTTP_409_CONFLICT, str(exc)) from exc
    if transaction is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Transaction not found")
    await db.commit()
    return TransactionOut.model_validate(transaction)


@router.delete(
    "/{transaction_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(verify_csrf)],
)
async def delete_transaction_route(
    transaction_id: uuid.UUID,
    current_user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> None:
    deleted = await delete_transaction(
        db, household_id=uuid.UUID(current_user.household_id), transaction_id=transaction_id
    )
    if not deleted:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Transaction not found")
    await db.commit()
