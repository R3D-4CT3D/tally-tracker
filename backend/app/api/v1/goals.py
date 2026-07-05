import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import CurrentUser, verify_csrf
from app.core.db import get_db
from app.schemas.goals import (
    GoalContributionCreate,
    GoalContributionOut,
    GoalCreate,
    GoalOut,
    GoalUpdate,
)
from app.services.goal_contributions import list_contributions, record_contribution
from app.services.goals import create_goal, delete_goal, get_goal, list_goals, update_goal
from app.services.transactions import InvalidReferenceError

router = APIRouter(prefix="/goals", tags=["goals"])


@router.post(
    "",
    response_model=GoalOut,
    dependencies=[Depends(verify_csrf)],
    status_code=status.HTTP_201_CREATED,
)
async def create_goal_route(
    payload: GoalCreate,
    current_user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> GoalOut:
    goal = await create_goal(db, household_id=uuid.UUID(current_user.household_id), payload=payload)
    await db.commit()
    return GoalOut.model_validate(goal)


@router.get("", response_model=list[GoalOut])
async def list_goals_route(
    current_user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> list[GoalOut]:
    goals = await list_goals(db, household_id=uuid.UUID(current_user.household_id))
    return [GoalOut.model_validate(g) for g in goals]


@router.get("/{goal_id}", response_model=GoalOut)
async def get_goal_route(
    goal_id: uuid.UUID,
    current_user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> GoalOut:
    goal = await get_goal(db, household_id=uuid.UUID(current_user.household_id), goal_id=goal_id)
    if goal is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Goal not found")
    return GoalOut.model_validate(goal)


@router.patch("/{goal_id}", response_model=GoalOut, dependencies=[Depends(verify_csrf)])
async def update_goal_route(
    goal_id: uuid.UUID,
    payload: GoalUpdate,
    current_user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> GoalOut:
    goal = await update_goal(
        db, household_id=uuid.UUID(current_user.household_id), goal_id=goal_id, payload=payload
    )
    if goal is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Goal not found")
    await db.commit()
    return GoalOut.model_validate(goal)


@router.delete(
    "/{goal_id}", status_code=status.HTTP_204_NO_CONTENT, dependencies=[Depends(verify_csrf)]
)
async def delete_goal_route(
    goal_id: uuid.UUID,
    current_user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> None:
    deleted = await delete_goal(
        db, household_id=uuid.UUID(current_user.household_id), goal_id=goal_id
    )
    if not deleted:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Goal not found")
    await db.commit()


@router.post(
    "/{goal_id}/contributions",
    response_model=GoalContributionOut,
    dependencies=[Depends(verify_csrf)],
    status_code=status.HTTP_201_CREATED,
)
async def record_contribution_route(
    goal_id: uuid.UUID,
    payload: GoalContributionCreate,
    current_user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> GoalContributionOut:
    try:
        contribution = await record_contribution(
            db,
            household_id=uuid.UUID(current_user.household_id),
            goal_id=goal_id,
            user_id=uuid.UUID(current_user.user_id),
            payload=payload,
        )
    except InvalidReferenceError as exc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, str(exc)) from exc
    if contribution is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Goal not found")
    await db.commit()
    return GoalContributionOut.model_validate(contribution)


@router.get("/{goal_id}/contributions", response_model=list[GoalContributionOut])
async def list_contributions_route(
    goal_id: uuid.UUID,
    current_user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> list[GoalContributionOut]:
    contributions = await list_contributions(
        db, household_id=uuid.UUID(current_user.household_id), goal_id=goal_id
    )
    return [GoalContributionOut.model_validate(c) for c in contributions]
