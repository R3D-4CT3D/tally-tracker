import uuid

from sqlalchemy import ForeignKey, Integer, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin, uuid7_default


class Checkin(Base, TimestampMixin):
    """One row per (user, iso week) -- recorded the first time a
    meaningful action (import, categorize, log a payment, contribute to a
    goal, complete a monthly close) happens in that week. iso_week is
    encoded as iso_year * 100 + iso_week (see Streak.last_checkin_week for
    why), not a bare week number.
    """

    __tablename__ = "checkins"
    __table_args__ = (UniqueConstraint("user_id", "iso_week"),)

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid7_default
    )
    household_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("households.id", ondelete="CASCADE")
    )
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    iso_week: Mapped[int] = mapped_column(Integer)
    actions_count: Mapped[int] = mapped_column(Integer, default=0)
