import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.balance_snapshot import BalanceSnapshot
from app.schemas.balance_snapshots import BalanceSnapshotListParams


async def list_balance_snapshots(
    db: AsyncSession, *, household_id: uuid.UUID, params: BalanceSnapshotListParams
) -> list[BalanceSnapshot]:
    stmt = select(BalanceSnapshot).where(BalanceSnapshot.household_id == household_id)
    if params.date_from is not None:
        stmt = stmt.where(BalanceSnapshot.date >= params.date_from)
    if params.date_to is not None:
        stmt = stmt.where(BalanceSnapshot.date <= params.date_to)
    stmt = stmt.order_by(BalanceSnapshot.date.desc()).limit(params.limit)
    result = await db.execute(stmt)
    return list(result.scalars().all())
