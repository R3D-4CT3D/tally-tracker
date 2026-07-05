import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.goal import Goal
from app.schemas.goals import GoalCreate, GoalUpdate


async def create_goal(db: AsyncSession, *, household_id: uuid.UUID, payload: GoalCreate) -> Goal:
    goal = Goal(household_id=household_id, **payload.model_dump())
    db.add(goal)
    await db.flush()
    return goal


async def list_goals(db: AsyncSession, *, household_id: uuid.UUID) -> list[Goal]:
    stmt = select(Goal).where(Goal.household_id == household_id).order_by(Goal.created_at)
    result = await db.execute(stmt)
    return list(result.scalars().all())


async def get_goal(db: AsyncSession, *, household_id: uuid.UUID, goal_id: uuid.UUID) -> Goal | None:
    stmt = select(Goal).where(Goal.household_id == household_id, Goal.id == goal_id)
    result = await db.execute(stmt)
    return result.scalar_one_or_none()


async def update_goal(
    db: AsyncSession, *, household_id: uuid.UUID, goal_id: uuid.UUID, payload: GoalUpdate
) -> Goal | None:
    goal = await get_goal(db, household_id=household_id, goal_id=goal_id)
    if goal is None:
        return None
    for key, value in payload.model_dump(exclude_unset=True).items():
        setattr(goal, key, value)
    await db.flush()
    return goal


async def delete_goal(db: AsyncSession, *, household_id: uuid.UUID, goal_id: uuid.UUID) -> bool:
    """Goals have no `archived` column per the spec's schema sketch -- only
    `completed_at` -- so deletion is the only removal path, unlike
    Accounts/Bills/Debts.
    """
    goal = await get_goal(db, household_id=household_id, goal_id=goal_id)
    if goal is None:
        return False
    await db.delete(goal)
    await db.flush()
    return True
