import uuid
from datetime import date as date_type

from sqlalchemy import BigInteger, Date, ForeignKey, Index, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin, uuid7_default


class BalanceSnapshot(Base, TimestampMixin):
    __tablename__ = "balance_snapshots"
    __table_args__ = (
        # Not in the spec's literal column sketch -- required so the nightly
        # job (app/jobs/balance_snapshot.py) can upsert idempotently instead
        # of accumulating duplicate rows if it's ever re-run same-day.
        UniqueConstraint("household_id", "date"),
        Index("ix_balance_snapshots_household_date", "household_id", "date"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid7_default
    )
    household_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("households.id", ondelete="CASCADE"))
    date: Mapped[date_type] = mapped_column(Date)
    cash_cents: Mapped[int] = mapped_column(BigInteger)
    debt_cents: Mapped[int] = mapped_column(BigInteger)
