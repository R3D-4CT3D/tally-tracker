import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import CurrentUser, verify_csrf
from app.core.db import get_db
from app.schemas.import_profiles import ImportProfileCreate, ImportProfileOut
from app.services.import_profiles import (
    create_import_profile,
    delete_import_profile,
    list_import_profiles,
)

router = APIRouter(prefix="/import-profiles", tags=["import-profiles"])


@router.post(
    "",
    response_model=ImportProfileOut,
    dependencies=[Depends(verify_csrf)],
    status_code=status.HTTP_201_CREATED,
)
async def create_import_profile_route(
    payload: ImportProfileCreate,
    current_user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> ImportProfileOut:
    profile = await create_import_profile(
        db, household_id=uuid.UUID(current_user.household_id), payload=payload
    )
    await db.commit()
    return ImportProfileOut.model_validate(profile)


@router.get("", response_model=list[ImportProfileOut])
async def list_import_profiles_route(
    current_user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> list[ImportProfileOut]:
    profiles = await list_import_profiles(db, household_id=uuid.UUID(current_user.household_id))
    return [ImportProfileOut.model_validate(p) for p in profiles]


@router.delete(
    "/{profile_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(verify_csrf)],
)
async def delete_import_profile_route(
    profile_id: uuid.UUID,
    current_user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> None:
    deleted = await delete_import_profile(
        db, household_id=uuid.UUID(current_user.household_id), profile_id=profile_id
    )
    if not deleted:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Import profile not found")
    await db.commit()
