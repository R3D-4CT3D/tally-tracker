import uuid
from datetime import date as date_type
from datetime import datetime
from typing import Any

from sqlalchemy import Date, DateTime, ForeignKey, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin, uuid7_default


class MonthlyClose(Base, TimestampMixin):
    """The Community Chest ceremony's record -- one per household per
    calendar month. `snapshot` holds the computed recap (income/spend,
    debt movement, quest progress, net-worth delta) so re-viewing a past
    close doesn't need to recompute it from since-changed live data.
    """

    __tablename__ = "monthly_closes"
    __table_args__ = (UniqueConstraint("household_id", "month"),)

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid7_default
    )
    household_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("households.id", ondelete="CASCADE")
    )
    # First-of-month date, e.g. 2026-07-01 -- reuses the existing
    # date_type convention rather than a raw "YYYY-MM" string column.
    month: Mapped[date_type] = mapped_column(Date)
    completed_by: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"))
    completed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    # Never below D, per docs/product-principles.md's "no shame mechanics" --
    # enforced in app/services/monthly_close.py, not a DB CHECK constraint
    # (this codebase's established convention, see Literal-typed schemas).
    grade: Mapped[str] = mapped_column(String(1))
    snapshot: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict)
