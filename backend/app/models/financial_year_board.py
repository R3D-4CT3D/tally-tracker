import uuid
from datetime import date as date_type
from datetime import datetime

from sqlalchemy import BigInteger, Date, DateTime, ForeignKey, Index, Integer
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin, uuid7_default


class FinancialYearBoard(Base, TimestampMixin):
    """One row per household per board-year. The *active* board for a
    household is the row with completed_at IS NULL -- there is at most one
    at a time (get_or_create_active_board enforces this), so no separate
    "current board" pointer is needed anywhere else.

    Tiles themselves are never persisted here (or anywhere) -- see
    app/services/board.py's compute_board_layout, which derives the 52-tile
    layout from this row's year_start_date/current_week plus the household's
    live Goals/Debts/checkins at request time.
    """

    __tablename__ = "financial_year_boards"
    __table_args__ = (
        Index("ix_financial_year_boards_household_active", "household_id", "completed_at"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid7_default
    )
    household_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("households.id", ondelete="CASCADE")
    )
    year_start_date: Mapped[date_type] = mapped_column(Date)
    # 0..52 -- the tile index the token currently sits on (0 == GO).
    current_week: Mapped[int] = mapped_column(Integer, default=0)
    tax_return_cents: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
