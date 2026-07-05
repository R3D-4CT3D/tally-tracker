"""Nightly balance-snapshot job -- powers M5's dashboard sparklines.

No scheduler library or scheduler service exists yet (no APScheduler/celery,
and deploy/docker-compose.yml only runs caddy/api/db/redis). Invocation is a
standalone script rather than an in-process scheduler, run nightly via host
crontab:

    15 3 * * * docker compose -f deploy/docker-compose.yml exec -T api \
        python -m app.jobs.balance_snapshot

See deploy/README.md for the exact crontab line. A cron-driven one-shot
process needs no crash/restart-recovery story the way a long-lived
in-process scheduler thread would, which is the simplest choice for a
single self-hosted instance.

Known limitation, deliberately not solved here: `date.today()` resolves to
the container's (UTC) clock, not each household's wall-clock day, so the
snapshot date can be off by one relative to a household's local "today".
Acceptable skew for V1 trend-line sparklines -- true per-household
timezone-aware dating is deferred.
"""

import asyncio
import uuid
from datetime import date as date_type
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.account import Account
from app.models.balance_snapshot import BalanceSnapshot
from app.models.debt import Debt
from app.models.household import Household


async def _cash_cents_by_household(db: AsyncSession) -> dict[uuid.UUID, int]:
    stmt = (
        select(Account.household_id, Account.balance_cents)
        .where(Account.archived.is_(False))
    )
    result = await db.execute(stmt)
    totals: dict[uuid.UUID, int] = {}
    for household_id, balance_cents in result.all():
        totals[household_id] = totals.get(household_id, 0) + balance_cents
    return totals


async def _debt_cents_by_household(db: AsyncSession) -> dict[uuid.UUID, int]:
    stmt = select(Debt.household_id, Debt.current_balance_cents).where(
        Debt.archived.is_(False), Debt.paid_off_at.is_(None)
    )
    result = await db.execute(stmt)
    totals: dict[uuid.UUID, int] = {}
    for household_id, current_balance_cents in result.all():
        totals[household_id] = totals.get(household_id, 0) + current_balance_cents
    return totals


async def run_balance_snapshot(
    db: AsyncSession, *, as_of: date_type | None = None
) -> list[BalanceSnapshot]:
    """Upserts one BalanceSnapshot row per household for `as_of` (defaults to
    today), so re-running the job same-day is safe and idempotent.
    """
    snapshot_date = as_of if as_of is not None else datetime.now().date()

    cash_by_household = await _cash_cents_by_household(db)
    debt_by_household = await _debt_cents_by_household(db)

    household_ids_stmt = select(Household.id)
    household_ids = (await db.execute(household_ids_stmt)).scalars().all()

    snapshots = []
    for household_id in household_ids:
        cash_cents = cash_by_household.get(household_id, 0)
        debt_cents = debt_by_household.get(household_id, 0)

        existing_stmt = select(BalanceSnapshot).where(
            BalanceSnapshot.household_id == household_id, BalanceSnapshot.date == snapshot_date
        )
        existing = (await db.execute(existing_stmt)).scalar_one_or_none()
        if existing is not None:
            existing.cash_cents = cash_cents
            existing.debt_cents = debt_cents
            snapshots.append(existing)
        else:
            snapshot = BalanceSnapshot(
                household_id=household_id,
                date=snapshot_date,
                cash_cents=cash_cents,
                debt_cents=debt_cents,
            )
            db.add(snapshot)
            snapshots.append(snapshot)

    await db.flush()
    return snapshots


async def _main() -> None:
    from app.core.db import async_session_maker

    async with async_session_maker() as db:
        snapshots = await run_balance_snapshot(db)
        await db.commit()
        print(f"balance_snapshot: wrote {len(snapshots)} household snapshot(s)")


if __name__ == "__main__":
    asyncio.run(_main())
