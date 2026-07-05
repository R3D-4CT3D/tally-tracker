import uuid
from datetime import datetime

from sqlalchemy import DateTime, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin, uuid7_default


class User(Base, TimestampMixin):
    """Identity only — no household_id/role here.

    household_members is the sole source of truth for which household(s) a
    user belongs to and what role they hold there. See
    docs/adr/0005-users-vs-household-members-source-of-truth.md.
    """

    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid7_default
    )
    email: Mapped[str] = mapped_column(String(320), unique=True, index=True)
    display_name: Mapped[str] = mapped_column(String(255))
    password_hash: Mapped[str] = mapped_column(String(255))
    totp_secret: Mapped[str | None] = mapped_column(String(64), nullable=True)
    # Updated at each successful login -- see app/api/v1/auth.py's login route,
    # which captures the *previous* value before overwriting it, since that's
    # what the dashboard's "since you were here" feature needs to compare
    # against (M5).
    last_login_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
