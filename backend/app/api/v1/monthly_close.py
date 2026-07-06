import uuid
from datetime import date as date_type
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import CurrentUser, verify_csrf
from app.core.db import get_db
from app.schemas.monthly_close import (
    CompleteMonthlyCloseRequest,
    MonthlyCloseOut,
    MonthlyCloseSnapshot,
)
from app.services.board import record_checkin
from app.services.monthly_close import (
    complete_monthly_close,
    compute_monthly_close_snapshot,
    get_monthly_close,
    list_monthly_closes,
)

router = APIRouter(prefix="/monthly-close", tags=["monthly-close"])


@router.get("/preview", response_model=MonthlyCloseSnapshot)
async def preview_monthly_close_route(
    month: date_type,
    current_user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> MonthlyCloseSnapshot:
    """Not persisted -- powers the wizard's steps 1-5 (recap figures) before
    the user commits via /complete."""
    return await compute_monthly_close_snapshot(
        db, household_id=uuid.UUID(current_user.household_id), month=month
    )


@router.post("/complete", response_model=MonthlyCloseOut, dependencies=[Depends(verify_csrf)])
async def complete_monthly_close_route(
    payload: CompleteMonthlyCloseRequest,
    current_user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> MonthlyCloseOut:
    household_id = uuid.UUID(current_user.household_id)
    monthly_close = await complete_monthly_close(
        db,
        household_id=household_id,
        month=payload.month,
        completed_by=uuid.UUID(current_user.user_id),
    )
    # Completing the ceremony is itself a check-in-worthy action.
    await record_checkin(db, household_id=household_id, user_id=uuid.UUID(current_user.user_id))
    await db.commit()
    return MonthlyCloseOut.model_validate(monthly_close)


@router.get("", response_model=list[MonthlyCloseOut])
async def list_monthly_closes_route(
    current_user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> list[MonthlyCloseOut]:
    closes = await list_monthly_closes(db, household_id=uuid.UUID(current_user.household_id))
    return [MonthlyCloseOut.model_validate(c) for c in closes]


@router.get("/{month}", response_model=MonthlyCloseOut)
async def get_monthly_close_route(
    month: date_type,
    current_user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> MonthlyCloseOut:
    household_id = uuid.UUID(current_user.household_id)
    monthly_close = await get_monthly_close(db, household_id=household_id, month=month)
    if monthly_close is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Monthly close not found for that month")
    # A household member *viewing* an already-completed close is check-in
    # worthy too -- "completing it counts as a check-in for both users if
    # both view it" (only the completer's check-in happens in /complete;
    # this covers the second user opening it later).
    await record_checkin(db, household_id=household_id, user_id=uuid.UUID(current_user.user_id))
    await db.commit()
    return MonthlyCloseOut.model_validate(monthly_close)
