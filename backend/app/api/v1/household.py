import uuid
from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import CurrentUser
from app.core.db import get_db
from app.schemas.auth import MemberOut
from app.services.household import list_members

router = APIRouter(prefix="/household", tags=["household"])


@router.get("/members", response_model=list[MemberOut])
async def get_members(
    current_user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> list[MemberOut]:
    rows = await list_members(db, uuid.UUID(current_user.household_id))
    return [
        MemberOut(
            id=user.id,
            email=user.email,
            display_name=user.display_name,
            role=member.role,
            joined_at=member.created_at,
        )
        for user, member in rows
    ]
