import uuid
from datetime import date as date_type

from sqlalchemy import BigInteger, Date, ForeignKey, Index
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin, uuid7_default


class GoalContribution(Base, TimestampMixin):
    __tablename__ = "goal_contributions"
    __table_args__ = (
        Index("ix_goal_contributions_household_goal", "household_id", "goal_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid7_default
    )
    # Not in the spec's literal column list -- see bill_payments.household_id
    # for the same reasoning (direct scoping convention).
    household_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("households.id", ondelete="CASCADE")
    )
    goal_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("goals.id", ondelete="CASCADE"))
    transaction_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("transactions.id", ondelete="SET NULL"), nullable=True
    )
    amount_cents: Mapped[int] = mapped_column(BigInteger)
    date: Mapped[date_type] = mapped_column(Date)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"))
