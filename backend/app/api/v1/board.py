import uuid
from datetime import UTC, datetime
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import CurrentUser, verify_csrf
from app.core.db import get_db
from app.schemas.board import BoardOut, TaxReturnRequest
from app.schemas.transactions import TransactionCreate
from app.services.board import get_board, record_tax_return
from app.services.transactions import (
    DuplicateTransactionError,
    InvalidReferenceError,
    create_transaction,
)

router = APIRouter(prefix="/board", tags=["board"])


@router.get("", response_model=BoardOut)
async def get_board_route(
    current_user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> BoardOut:
    # A GET that still commits: get_or_create_active_board can create the
    # household's first board row or advance current_week via lazy
    # reconciliation -- both real writes, not just reads.
    board = await get_board(
        db,
        household_id=uuid.UUID(current_user.household_id),
        user_id=uuid.UUID(current_user.user_id),
    )
    await db.commit()
    return board


@router.post("/tax-return", response_model=BoardOut, dependencies=[Depends(verify_csrf)])
async def record_tax_return_route(
    payload: TaxReturnRequest,
    current_user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> BoardOut:
    """Resolves the passing-GO year-end prompt. amount_cents > 0 creates a
    real income Transaction on the chosen account (it actually affects cash
    totals, not just a cosmetic animation) before finalizing the board;
    amount_cents == 0 just finalizes it as "no return this year."
    """
    household_id = uuid.UUID(current_user.household_id)

    if payload.amount_cents > 0:
        assert payload.account_id is not None  # enforced by TaxReturnRequest's validator
        try:
            await create_transaction(
                db,
                household_id=household_id,
                created_by=uuid.UUID(current_user.user_id),
                payload=TransactionCreate(
                    account_id=payload.account_id,
                    date=datetime.now(UTC).date(),
                    amount_cents=payload.amount_cents,
                    description="Tax return",
                ),
            )
        except InvalidReferenceError as exc:
            raise HTTPException(status.HTTP_404_NOT_FOUND, str(exc)) from exc
        except DuplicateTransactionError as exc:
            raise HTTPException(status.HTTP_409_CONFLICT, str(exc)) from exc

    board = await record_tax_return(
        db, household_id=household_id, amount_cents=payload.amount_cents
    )
    if board is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "No finished board awaiting a tax return")

    result = await get_board(
        db, household_id=household_id, user_id=uuid.UUID(current_user.user_id)
    )
    await db.commit()
    return result
