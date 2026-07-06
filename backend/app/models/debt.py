import uuid
from datetime import datetime

from sqlalchemy import BigInteger, Boolean, DateTime, ForeignKey, Integer, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin, uuid7_default


class Debt(Base, TimestampMixin):
    __tablename__ = "debts"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid7_default
    )
    household_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("households.id", ondelete="CASCADE"), index=True
    )
    name: Mapped[str] = mapped_column(String(255))
    type: Mapped[str] = mapped_column(String(20))
    original_balance_cents: Mapped[int] = mapped_column(BigInteger)
    current_balance_cents: Mapped[int] = mapped_column(BigInteger)
    # Basis points, not cents -- an APR isn't money (e.g. 1999 == 19.99%).
    apr_bps: Mapped[int] = mapped_column(Integer)
    min_payment_cents: Mapped[int] = mapped_column(BigInteger)
    due_day: Mapped[int] = mapped_column(Integer)
    paid_off_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    archived: Mapped[bool] = mapped_column(Boolean, default=False)
    # Nullable (unlike Goal.icon/color, which are required) -- existing debts
    # predate these columns and nothing forces a user to backfill them. Purely
    # for the Monopoly board's property-card styling (mortgage/railroad tiles).
    icon: Mapped[str | None] = mapped_column(String(32), nullable=True)
    color: Mapped[str | None] = mapped_column(String(7), nullable=True)
