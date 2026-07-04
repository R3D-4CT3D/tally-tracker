import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.import_profile import ImportProfile
from app.schemas.import_profiles import ImportProfileCreate


async def create_import_profile(
    db: AsyncSession, *, household_id: uuid.UUID, payload: ImportProfileCreate
) -> ImportProfile:
    profile = ImportProfile(
        household_id=household_id,
        name=payload.name,
        column_mapping=payload.column_mapping.model_dump(),
        date_format=payload.date_format,
        source_hint=payload.source_hint,
    )
    db.add(profile)
    await db.flush()
    return profile


async def list_import_profiles(
    db: AsyncSession, *, household_id: uuid.UUID
) -> list[ImportProfile]:
    stmt = (
        select(ImportProfile)
        .where(ImportProfile.household_id == household_id)
        .order_by(ImportProfile.name)
    )
    result = await db.execute(stmt)
    return list(result.scalars().all())


async def get_import_profile(
    db: AsyncSession, *, household_id: uuid.UUID, profile_id: uuid.UUID
) -> ImportProfile | None:
    stmt = select(ImportProfile).where(
        ImportProfile.household_id == household_id, ImportProfile.id == profile_id
    )
    result = await db.execute(stmt)
    return result.scalar_one_or_none()


async def delete_import_profile(
    db: AsyncSession, *, household_id: uuid.UUID, profile_id: uuid.UUID
) -> bool:
    profile = await get_import_profile(db, household_id=household_id, profile_id=profile_id)
    if profile is None:
        return False
    await db.delete(profile)
    await db.flush()
    return True
