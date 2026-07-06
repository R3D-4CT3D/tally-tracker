import uuid

from sqlalchemy import ForeignKey, Integer, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin, uuid7_default


class Streak(Base, TimestampMixin):
    """Per-user weekly check-in streak. household_id is not in the spec's
    literal column list -- added for the same direct-scoping reason as
    bill_payments/goal_contributions (listing a household's streaks without
    it would require joining through users).

    freezes_banked is "Get Out of Jail Free" cards in the product's own
    vocabulary (see docs/product-principles.md) -- kept as this literal
    column name since the rename is UI copy only, not a schema concept.
    """

    __tablename__ = "streaks"
    __table_args__ = (UniqueConstraint("household_id", "user_id"),)

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid7_default
    )
    household_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("households.id", ondelete="CASCADE")
    )
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    current_weeks: Mapped[int] = mapped_column(Integer, default=0)
    best_weeks: Mapped[int] = mapped_column(Integer, default=0)
    freezes_banked: Mapped[int] = mapped_column(Integer, default=0)
    # Encoded as iso_year * 100 + iso_week (see app/services/board.py's
    # _iso_week_key) so it stays a single sortable, globally-unique integer
    # across year boundaries -- a bare ISO week number would collide between
    # e.g. week 1 of 2026 and week 1 of 2027. Lets lazy reconciliation tell
    # "already advanced this week" apart from "N weeks behind."
    last_checkin_week: Mapped[int | None] = mapped_column(Integer, nullable=True)
