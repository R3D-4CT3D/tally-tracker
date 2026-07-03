import uuid
from datetime import UTC, datetime, timedelta

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.security import generate_invite_token, hash_invite_token, hash_password
from app.models.household_member import HouseholdMember
from app.models.invite import Invite
from app.models.user import User

settings = get_settings()


class InviteError(Exception):
    """Raised for any invalid/expired/used/conflicting invite. Callers should
    surface the same generic message for every case, to avoid leaking which
    invites (or emails) exist.
    """


async def create_invite(
    db: AsyncSession, *, household_id: uuid.UUID, created_by: uuid.UUID
) -> tuple[Invite, str]:
    token = generate_invite_token()
    invite = Invite(
        household_id=household_id,
        code_hash=hash_invite_token(token),
        created_by=created_by,
        expires_at=datetime.now(UTC) + timedelta(days=settings.invite_expiry_days),
    )
    db.add(invite)
    await db.flush()
    return invite, token


async def list_invites(db: AsyncSession, household_id: uuid.UUID) -> list[Invite]:
    stmt = (
        select(Invite)
        .where(Invite.household_id == household_id)
        .order_by(Invite.created_at.desc())
    )
    result = await db.execute(stmt)
    return list(result.scalars().all())


async def accept_invite(
    db: AsyncSession,
    *,
    token: str,
    email: str,
    display_name: str,
    password: str,
) -> tuple[User, HouseholdMember]:
    code_hash = hash_invite_token(token)
    stmt = select(Invite).where(Invite.code_hash == code_hash)
    result = await db.execute(stmt)
    invite = result.scalar_one_or_none()

    if invite is None or invite.used_at is not None or invite.expires_at < datetime.now(UTC):
        raise InviteError("Invalid or expired invite")

    existing_stmt = select(User).where(User.email == email.lower())
    existing_result = await db.execute(existing_stmt)
    if existing_result.scalar_one_or_none() is not None:
        raise InviteError("Invalid or expired invite")

    user = User(
        email=email.lower(),
        display_name=display_name,
        password_hash=hash_password(password),
    )
    db.add(user)
    await db.flush()

    member = HouseholdMember(household_id=invite.household_id, user_id=user.id, role="member")
    db.add(member)

    invite.used_by = user.id
    invite.used_at = datetime.now(UTC)

    await db.flush()
    return user, member
