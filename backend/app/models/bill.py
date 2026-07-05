import uuid
from datetime import date as date_type

from sqlalchemy import BigInteger, Boolean, Date, ForeignKey, Integer, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin, uuid7_default


class Bill(Base, TimestampMixin):
    __tablename__ = "bills"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid7_default
    )
    household_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("households.id", ondelete="CASCADE"), index=True
    )
    name: Mapped[str] = mapped_column(String(255))
    amount_cents: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    is_variable: Mapped[bool] = mapped_column(Boolean, default=False)
    frequency: Mapped[str] = mapped_column(String(20))
    due_day: Mapped[int] = mapped_column(Integer)
    # Only meaningful when frequency == "custom" -- not in the spec's literal
    # column sketch, added because "custom" needs a defined interval to roll
    # next_due_date forward by (see app/services/bill_payments.py).
    custom_interval_days: Mapped[int | None] = mapped_column(Integer, nullable=True)
    account_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("accounts.id", ondelete="SET NULL"), nullable=True
    )
    category_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("categories.id", ondelete="SET NULL"), nullable=True
    )
    autopay: Mapped[bool] = mapped_column(Boolean, default=False)
    next_due_date: Mapped[date_type] = mapped_column(Date)
    archived: Mapped[bool] = mapped_column(Boolean, default=False)
