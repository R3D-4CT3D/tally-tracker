import uuid

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import hash_password
from app.models.household import Household
from app.models.household_member import HouseholdMember
from app.models.user import User


async def is_setup_complete(db: AsyncSession) -> bool:
    result = await db.execute(select(func.count()).select_from(Household))
    return (result.scalar_one() or 0) > 0


async def create_household_and_owner(
    db: AsyncSession,
    *,
    household_name: str,
    owner_email: str,
    owner_display_name: str,
    owner_password: str,
) -> tuple[Household, User, HouseholdMember]:
    """Creates the household + owner atomically. Callers must guard this with
    is_setup_complete() first — this function itself doesn't re-check, since
    the M1 test suite also uses it directly to seed a *second* household
    (bypassing the app-level "setup runs once" gate, which lives in the
    /setup route, not here) to exercise cross-household isolation.
    """
    household = Household(name=household_name)
    db.add(household)
    await db.flush()

    user = User(
        email=owner_email.lower(),
        display_name=owner_display_name,
        password_hash=hash_password(owner_password),
    )
    db.add(user)
    await db.flush()

    member = HouseholdMember(household_id=household.id, user_id=user.id, role="owner")
    db.add(member)
    await db.flush()

    return household, user, member


async def list_members(
    db: AsyncSession, household_id: uuid.UUID
) -> list[tuple[User, HouseholdMember]]:
    stmt = (
        select(User, HouseholdMember)
        .join(HouseholdMember, HouseholdMember.user_id == User.id)
        .where(HouseholdMember.household_id == household_id)
        .order_by(HouseholdMember.created_at)
    )
    result = await db.execute(stmt)
    return [(user, member) for user, member in result]
