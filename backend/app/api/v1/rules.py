import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import CurrentUser, verify_csrf
from app.core.db import get_db
from app.schemas.rules import RuleCreate, RuleOut, RuleReorderRequest, RuleUpdate
from app.services.rules import (
    RuleError,
    create_rule,
    delete_rule,
    list_rules,
    reorder_rules,
    update_rule,
)
from app.services.transactions import InvalidReferenceError

router = APIRouter(prefix="/rules", tags=["rules"])


@router.post(
    "",
    response_model=RuleOut,
    dependencies=[Depends(verify_csrf)],
    status_code=status.HTTP_201_CREATED,
)
async def create_rule_route(
    payload: RuleCreate,
    current_user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> RuleOut:
    try:
        rule = await create_rule(
            db, household_id=uuid.UUID(current_user.household_id), payload=payload
        )
    except RuleError as exc:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, str(exc)) from exc
    except InvalidReferenceError as exc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, str(exc)) from exc
    await db.commit()
    return RuleOut.model_validate(rule)


@router.get("", response_model=list[RuleOut])
async def list_rules_route(
    current_user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> list[RuleOut]:
    rules = await list_rules(db, household_id=uuid.UUID(current_user.household_id))
    return [RuleOut.model_validate(r) for r in rules]


@router.patch("/{rule_id}", response_model=RuleOut, dependencies=[Depends(verify_csrf)])
async def update_rule_route(
    rule_id: uuid.UUID,
    payload: RuleUpdate,
    current_user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> RuleOut:
    try:
        rule = await update_rule(
            db,
            household_id=uuid.UUID(current_user.household_id),
            rule_id=rule_id,
            payload=payload,
        )
    except RuleError as exc:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, str(exc)) from exc
    except InvalidReferenceError as exc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, str(exc)) from exc
    if rule is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Rule not found")
    await db.commit()
    return RuleOut.model_validate(rule)


@router.delete(
    "/{rule_id}", status_code=status.HTTP_204_NO_CONTENT, dependencies=[Depends(verify_csrf)]
)
async def delete_rule_route(
    rule_id: uuid.UUID,
    current_user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> None:
    deleted = await delete_rule(
        db, household_id=uuid.UUID(current_user.household_id), rule_id=rule_id
    )
    if not deleted:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Rule not found")
    await db.commit()


@router.post("/reorder", response_model=list[RuleOut], dependencies=[Depends(verify_csrf)])
async def reorder_rules_route(
    payload: RuleReorderRequest,
    current_user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> list[RuleOut]:
    try:
        rules = await reorder_rules(
            db,
            household_id=uuid.UUID(current_user.household_id),
            ordered_ids=payload.ordered_ids,
        )
    except RuleError as exc:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, str(exc)) from exc
    await db.commit()
    return [RuleOut.model_validate(r) for r in rules]
