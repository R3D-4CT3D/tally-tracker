import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import CurrentUser, verify_csrf
from app.core.db import get_db
from app.schemas.bills import (
    BillCreate,
    BillMarkPaidRequest,
    BillOut,
    BillPaymentOut,
    BillUpdate,
)
from app.services.bill_payments import list_bill_payments, mark_bill_paid
from app.services.bills import (
    BillValidationError,
    archive_bill,
    create_bill,
    get_bill,
    list_bills,
    update_bill,
)
from app.services.transactions import DuplicateTransactionError, InvalidReferenceError

router = APIRouter(prefix="/bills", tags=["bills"])


@router.post(
    "",
    response_model=BillOut,
    dependencies=[Depends(verify_csrf)],
    status_code=status.HTTP_201_CREATED,
)
async def create_bill_route(
    payload: BillCreate,
    current_user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> BillOut:
    try:
        bill = await create_bill(
            db, household_id=uuid.UUID(current_user.household_id), payload=payload
        )
    except BillValidationError as exc:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, str(exc)) from exc
    except InvalidReferenceError as exc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, str(exc)) from exc
    await db.commit()
    return BillOut.model_validate(bill)


@router.get("", response_model=list[BillOut])
async def list_bills_route(
    current_user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
    include_archived: bool = False,
) -> list[BillOut]:
    bills = await list_bills(
        db, household_id=uuid.UUID(current_user.household_id), include_archived=include_archived
    )
    return [BillOut.model_validate(b) for b in bills]


@router.get("/{bill_id}", response_model=BillOut)
async def get_bill_route(
    bill_id: uuid.UUID,
    current_user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> BillOut:
    bill = await get_bill(db, household_id=uuid.UUID(current_user.household_id), bill_id=bill_id)
    if bill is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Bill not found")
    return BillOut.model_validate(bill)


@router.patch("/{bill_id}", response_model=BillOut, dependencies=[Depends(verify_csrf)])
async def update_bill_route(
    bill_id: uuid.UUID,
    payload: BillUpdate,
    current_user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> BillOut:
    try:
        bill = await update_bill(
            db, household_id=uuid.UUID(current_user.household_id), bill_id=bill_id, payload=payload
        )
    except BillValidationError as exc:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, str(exc)) from exc
    except InvalidReferenceError as exc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, str(exc)) from exc
    if bill is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Bill not found")
    await db.commit()
    return BillOut.model_validate(bill)


@router.post(
    "/{bill_id}/archive",
    response_model=BillOut,
    dependencies=[Depends(verify_csrf)],
)
async def archive_bill_route(
    bill_id: uuid.UUID,
    current_user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> BillOut:
    bill = await archive_bill(
        db, household_id=uuid.UUID(current_user.household_id), bill_id=bill_id
    )
    if bill is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Bill not found")
    await db.commit()
    return BillOut.model_validate(bill)


@router.post(
    "/{bill_id}/mark-paid",
    response_model=BillPaymentOut,
    dependencies=[Depends(verify_csrf)],
    status_code=status.HTTP_201_CREATED,
)
async def mark_bill_paid_route(
    bill_id: uuid.UUID,
    payload: BillMarkPaidRequest,
    current_user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> BillPaymentOut:
    try:
        payment = await mark_bill_paid(
            db,
            household_id=uuid.UUID(current_user.household_id),
            bill_id=bill_id,
            created_by=uuid.UUID(current_user.user_id),
            payload=payload,
        )
    except BillValidationError as exc:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, str(exc)) from exc
    except InvalidReferenceError as exc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, str(exc)) from exc
    except DuplicateTransactionError as exc:
        raise HTTPException(status.HTTP_409_CONFLICT, str(exc)) from exc
    if payment is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Bill not found")
    await db.commit()
    return BillPaymentOut.model_validate(payment)


@router.get("/{bill_id}/payments", response_model=list[BillPaymentOut])
async def list_bill_payments_route(
    bill_id: uuid.UUID,
    current_user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> list[BillPaymentOut]:
    payments = await list_bill_payments(
        db, household_id=uuid.UUID(current_user.household_id), bill_id=bill_id
    )
    return [BillPaymentOut.model_validate(p) for p in payments]
