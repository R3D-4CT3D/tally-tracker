import uuid
from datetime import date as date_type
from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import CurrentUser
from app.core.db import get_db
from app.schemas.balance_snapshots import BalanceSnapshotListParams, BalanceSnapshotOut
from app.services.balance_snapshots import list_balance_snapshots

router = APIRouter(prefix="/balance-snapshots", tags=["balance-snapshots"])


@router.get("", response_model=list[BalanceSnapshotOut])
async def list_balance_snapshots_route(
    current_user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
    date_from: date_type | None = None,
    date_to: date_type | None = None,
    limit: int = 90,
) -> list[BalanceSnapshotOut]:
    params = BalanceSnapshotListParams(date_from=date_from, date_to=date_to, limit=limit)
    snapshots = await list_balance_snapshots(
        db, household_id=uuid.UUID(current_user.household_id), params=params
    )
    return [BalanceSnapshotOut.model_validate(s) for s in snapshots]
