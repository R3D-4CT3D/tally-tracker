import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.trophy import Trophy


async def record_trophy(
    db: AsyncSession,
    *,
    household_id: uuid.UUID,
    kind: str,
    ref_id: uuid.UUID,
    stats: dict[str, Any],
) -> Trophy:
    """Called at the exact moment a Goal/Debt transitions to settled --
    never retroactively, so `stats` captures state as of that moment even
    if the referenced entity changes later (e.g. a debt's balance moving
    back above zero after this fires, which flips paid_off_at back off
    without touching the trophy already earned)."""
    trophy = Trophy(
        household_id=household_id,
        kind=kind,
        ref_id=ref_id,
        earned_at=datetime.now(UTC),
        stats=stats,
    )
    db.add(trophy)
    await db.flush()
    return trophy
