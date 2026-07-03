import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Response, status
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import require_role, verify_csrf
from app.core.db import get_db
from app.core.redis import get_redis
from app.core.security import SessionData, set_session_cookies
from app.models.household import Household
from app.schemas.auth import InviteAcceptRequest, InviteCreateResponse, InviteOut
from app.services.audit import record_audit_event
from app.services.auth import create_session_for_user
from app.services.invites import InviteError, accept_invite, create_invite, list_invites

router = APIRouter(prefix="/invites", tags=["invites"])


@router.post("", response_model=InviteCreateResponse, dependencies=[Depends(verify_csrf)])
async def create_invite_route(
    current_user: Annotated[SessionData, require_role("owner")],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> InviteCreateResponse:
    invite, token = await create_invite(
        db,
        household_id=uuid.UUID(current_user.household_id),
        created_by=uuid.UUID(current_user.user_id),
    )
    await record_audit_event(
        db,
        household_id=invite.household_id,
        user_id=uuid.UUID(current_user.user_id),
        action="invite_created",
        entity="invite",
        entity_id=invite.id,
    )
    await db.commit()
    return InviteCreateResponse(token=token, expires_at=invite.expires_at)


@router.get("", response_model=list[InviteOut])
async def list_invites_route(
    current_user: Annotated[SessionData, require_role("owner")],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> list[InviteOut]:
    invites = await list_invites(db, uuid.UUID(current_user.household_id))
    return [
        InviteOut(id=i.id, expires_at=i.expires_at, used_at=i.used_at, created_at=i.created_at)
        for i in invites
    ]


@router.post("/accept")
async def accept_invite_route(
    payload: InviteAcceptRequest,
    response: Response,
    db: Annotated[AsyncSession, Depends(get_db)],
    redis: Annotated[Redis, Depends(get_redis)],
) -> dict[str, str]:
    try:
        user, member = await accept_invite(
            db,
            token=payload.token,
            email=payload.email,
            display_name=payload.display_name,
            password=payload.password,
        )
    except InviteError as exc:
        await db.rollback()
        raise HTTPException(status.HTTP_400_BAD_REQUEST, str(exc)) from exc

    household = await db.get(Household, member.household_id)
    assert household is not None

    await record_audit_event(
        db,
        household_id=household.id,
        user_id=user.id,
        action="invite_accepted",
        entity="household_member",
        entity_id=member.id,
    )
    await db.commit()

    session = await create_session_for_user(redis, user, member, household)
    set_session_cookies(response, session)
    return {"status": "ok"}
