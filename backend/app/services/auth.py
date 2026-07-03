from redis.asyncio import Redis
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.security import SessionData, create_session, verify_password
from app.models.household import Household
from app.models.household_member import HouseholdMember
from app.models.user import User

settings = get_settings()


async def authenticate_user(
    db: AsyncSession, email: str, password: str
) -> tuple[User, HouseholdMember] | None:
    """Generic, timing-safe: verifies against a dummy hash when the email
    doesn't match any user, so response time doesn't leak which branch ran.
    """
    stmt = select(User).where(User.email == email.lower())
    result = await db.execute(stmt)
    user = result.scalar_one_or_none()

    password_hash = user.password_hash if user is not None else None
    ok = verify_password(password, password_hash)
    if not ok or user is None:
        return None

    member_stmt = select(HouseholdMember).where(HouseholdMember.user_id == user.id)
    member_result = await db.execute(member_stmt)
    member = member_result.scalar_one_or_none()
    if member is None:
        return None
    return user, member


async def create_session_for_user(
    redis: Redis, user: User, member: HouseholdMember, household: Household
) -> SessionData:
    return await create_session(
        redis,
        user_id=str(user.id),
        household_id=str(household.id),
        household_name=household.name,
        role=member.role,
        email=user.email,
        display_name=user.display_name,
        idle_days=settings.session_idle_days,
        absolute_days=settings.session_absolute_days,
    )
