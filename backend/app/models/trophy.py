import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import DateTime, ForeignKey, String
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin, uuid7_default


class Trophy(Base, TimestampMixin):
    """A permanent record of a board milestone -- a goal reaching its
    target, a debt reaching zero, a year passing GO. `ref_id` points at the
    goal/debt/board row that earned it (no FK -- the referenced table
    varies by `kind`, same reasoning as ImportBatch not FK-ing a variable
    target). `stats` is a small freeform snapshot (e.g. payoff duration,
    final balance) captured at earn time so it survives later edits to the
    referenced entity.
    """

    __tablename__ = "trophies"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid7_default
    )
    household_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("households.id", ondelete="CASCADE")
    )
    kind: Mapped[str] = mapped_column(String(30))
    ref_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True))
    earned_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    stats: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict)
