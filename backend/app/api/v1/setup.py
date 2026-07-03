from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_db
from app.core.redis import get_redis
from app.core.security import set_session_cookies
from app.schemas.auth import SetupRequest, SetupStatus
from app.services.audit import record_audit_event
from app.services.auth import create_session_for_user
from app.services.household import create_household_and_owner, is_setup_complete

router = APIRouter(tags=["setup"])


@router.get("/setup/status", response_model=SetupStatus)
async def setup_status(db: Annotated[AsyncSession, Depends(get_db)]) -> SetupStatus:
    return SetupStatus(is_setup=await is_setup_complete(db))


@router.post("/setup", status_code=status.HTTP_201_CREATED)
async def setup(
    payload: SetupRequest,
    request: Request,
    response: Response,
    db: Annotated[AsyncSession, Depends(get_db)],
    redis: Annotated[Redis, Depends(get_redis)],
) -> dict[str, str]:
    """Runs once: creates the instance's household + owner. Subsequent calls
    return 409 so the frontend can redirect to login instead.
    """
    if await is_setup_complete(db):
        raise HTTPException(status.HTTP_409_CONFLICT, "Setup has already been completed")

    household, user, member = await create_household_and_owner(
        db,
        household_name=payload.household_name,
        owner_email=payload.owner_email,
        owner_display_name=payload.owner_display_name,
        owner_password=payload.owner_password,
    )
    await record_audit_event(
        db,
        household_id=household.id,
        user_id=user.id,
        action="setup_completed",
        entity="household",
        entity_id=household.id,
        ip=request.client.host if request.client else None,
    )
    await db.commit()

    session = await create_session_for_user(redis, user, member, household)
    set_session_cookies(response, session)
    return {"status": "ok"}
