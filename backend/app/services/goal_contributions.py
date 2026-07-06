import uuid
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.goal_contribution import GoalContribution
from app.schemas.goals import GoalContributionCreate
from app.services.goals import get_goal
from app.services.transactions import InvalidReferenceError, get_transaction
from app.services.trophies import record_trophy


async def record_contribution(
    db: AsyncSession,
    *,
    household_id: uuid.UUID,
    goal_id: uuid.UUID,
    user_id: uuid.UUID,
    payload: GoalContributionCreate,
) -> GoalContribution | None:
    goal = await get_goal(db, household_id=household_id, goal_id=goal_id)
    if goal is None:
        return None

    if payload.transaction_id is not None:
        transaction = await get_transaction(
            db, household_id=household_id, transaction_id=payload.transaction_id
        )
        if transaction is None:
            raise InvalidReferenceError("Transaction not found")

    contribution = GoalContribution(
        household_id=household_id,
        goal_id=goal.id,
        transaction_id=payload.transaction_id,
        amount_cents=payload.amount_cents,
        date=payload.date,
        user_id=user_id,
    )
    goal.current_cents += payload.amount_cents
    # One-way in this milestone's scope: there's no delete-contribution
    # endpoint, so completed_at never needs to be un-set the way
    # debts.paid_off_at does (see app/services/debts.py's symmetric
    # _maybe_toggle_paid_off) -- a deliberate, accepted asymmetry, not an
    # oversight.
    newly_completed = goal.current_cents >= goal.target_cents and goal.completed_at is None
    if newly_completed:
        goal.completed_at = datetime.now(UTC)
    db.add(contribution)
    await db.flush()
    if newly_completed:
        await record_trophy(
            db,
            household_id=household_id,
            kind="goal_complete",
            ref_id=goal.id,
            stats={"name": goal.name, "target_cents": goal.target_cents},
        )
    return contribution


async def list_contributions(
    db: AsyncSession, *, household_id: uuid.UUID, goal_id: uuid.UUID
) -> list[GoalContribution]:
    stmt = (
        select(GoalContribution)
        .where(GoalContribution.household_id == household_id, GoalContribution.goal_id == goal_id)
        .order_by(GoalContribution.date.desc())
    )
    result = await db.execute(stmt)
    return list(result.scalars().all())
