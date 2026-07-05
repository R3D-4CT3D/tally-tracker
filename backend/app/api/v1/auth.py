import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import CurrentUser, verify_csrf
from app.core.db import get_db
from app.core.limiter import cache_login_email, limiter, login_rate_limit_key
from app.core.redis import get_redis
from app.core.security import clear_session_cookies, delete_session, set_session_cookies
from app.models.household import Household
from app.schemas.auth import LoginRequest, MeResponse
from app.services.audit import record_audit_event
from app.services.auth import authenticate_user, create_session_for_user, record_login

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/login", dependencies=[Depends(cache_login_email)])
@limiter.limit("5/15minutes", key_func=login_rate_limit_key)
async def login(
    request: Request,
    payload: LoginRequest,
    response: Response,
    db: Annotated[AsyncSession, Depends(get_db)],
    redis: Annotated[Redis, Depends(get_redis)],
) -> dict[str, str]:
    ip = request.client.host if request.client else None
    result = await authenticate_user(db, payload.email, payload.password)

    if result is None:
        await record_audit_event(
            db,
            household_id=None,
            user_id=None,
            action="login_failed",
            entity="user",
            ip=ip,
        )
        await db.commit()
        # Generic message regardless of whether the email exists.
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid email or password")

    user, member = result
    household = await db.get(Household, member.household_id)
    assert household is not None  # FK guarantees this; narrows the type for mypy

    previous_last_login = record_login(user)

    await record_audit_event(
        db,
        household_id=household.id,
        user_id=user.id,
        action="login_success",
        entity="user",
        entity_id=user.id,
        ip=ip,
    )
    await db.commit()

    session = await create_session_for_user(
        redis, user, member, household, last_login_at=previous_last_login
    )
    set_session_cookies(response, session)
    return {"status": "ok"}


@router.post("/logout", dependencies=[Depends(verify_csrf)])
async def logout(
    response: Response,
    current_user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
    redis: Annotated[Redis, Depends(get_redis)],
) -> dict[str, str]:
    await delete_session(redis, current_user.session_id, current_user.user_id)
    await record_audit_event(
        db,
        household_id=uuid.UUID(current_user.household_id),
        user_id=uuid.UUID(current_user.user_id),
        action="logout",
        entity="user",
        entity_id=uuid.UUID(current_user.user_id),
    )
    await db.commit()
    clear_session_cookies(response)
    return {"status": "ok"}


@router.get("/me", response_model=MeResponse)
async def me(current_user: CurrentUser) -> MeResponse:
    return MeResponse(
        user_id=uuid.UUID(current_user.user_id),
        email=current_user.email,
        display_name=current_user.display_name,
        role=current_user.role,
        household_id=uuid.UUID(current_user.household_id),
        household_name=current_user.household_name,
        last_login_at=current_user.last_login_at,
    )
