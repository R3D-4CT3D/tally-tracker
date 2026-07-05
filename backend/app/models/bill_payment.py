import uuid
from datetime import date as date_type

from sqlalchemy import BigInteger, Date, ForeignKey, Index, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin, uuid7_default


class BillPayment(Base, TimestampMixin):
    __tablename__ = "bill_payments"
    __table_args__ = (Index("ix_bill_payments_household_bill", "household_id", "bill_id"),)

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid7_default
    )
    # Not in the spec's literal column list for bill_payments -- added so this
    # table follows the same "every household-owned table carries
    # household_id directly" convention as everything else (no relationship()
    # anywhere, so listing/scoping without it would require joining through
    # bills, which the codebase avoids).
    household_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("households.id", ondelete="CASCADE")
    )
    bill_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("bills.id", ondelete="CASCADE"))
    transaction_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("transactions.id", ondelete="SET NULL"), nullable=True
    )
    due_date: Mapped[date_type] = mapped_column(Date)
    paid_date: Mapped[date_type | None] = mapped_column(Date, nullable=True)
    amount_cents: Mapped[int] = mapped_column(BigInteger)
    status: Mapped[str] = mapped_column(String(20))
