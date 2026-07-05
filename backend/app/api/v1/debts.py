import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import CurrentUser, verify_csrf
from app.core.db import get_db
from app.schemas.debts import DebtCreate, DebtOut, DebtUpdate
from app.services.debts import archive_debt, create_debt, get_debt, list_debts, update_debt

router = APIRouter(prefix="/debts", tags=["debts"])


@router.post(
    "",
    response_model=DebtOut,
    dependencies=[Depends(verify_csrf)],
    status_code=status.HTTP_201_CREATED,
)
async def create_debt_route(
    payload: DebtCreate,
    current_user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> DebtOut:
    debt = await create_debt(db, household_id=uuid.UUID(current_user.household_id), payload=payload)
    await db.commit()
    return DebtOut.model_validate(debt)


@router.get("", response_model=list[DebtOut])
async def list_debts_route(
    current_user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
    include_archived: bool = False,
) -> list[DebtOut]:
    debts = await list_debts(
        db, household_id=uuid.UUID(current_user.household_id), include_archived=include_archived
    )
    return [DebtOut.model_validate(d) for d in debts]


@router.get("/{debt_id}", response_model=DebtOut)
async def get_debt_route(
    debt_id: uuid.UUID,
    current_user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> DebtOut:
    debt = await get_debt(db, household_id=uuid.UUID(current_user.household_id), debt_id=debt_id)
    if debt is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Debt not found")
    return DebtOut.model_validate(debt)


@router.patch("/{debt_id}", response_model=DebtOut, dependencies=[Depends(verify_csrf)])
async def update_debt_route(
    debt_id: uuid.UUID,
    payload: DebtUpdate,
    current_user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> DebtOut:
    debt = await update_debt(
        db, household_id=uuid.UUID(current_user.household_id), debt_id=debt_id, payload=payload
    )
    if debt is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Debt not found")
    await db.commit()
    return DebtOut.model_validate(debt)


@router.post(
    "/{debt_id}/archive",
    response_model=DebtOut,
    dependencies=[Depends(verify_csrf)],
)
async def archive_debt_route(
    debt_id: uuid.UUID,
    current_user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> DebtOut:
    debt = await archive_debt(
        db, household_id=uuid.UUID(current_user.household_id), debt_id=debt_id
    )
    if debt is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Debt not found")
    await db.commit()
    return DebtOut.model_validate(debt)
