import uuid
from datetime import date as date_type
from datetime import datetime

from sqlalchemy import BigInteger, Date, DateTime, ForeignKey, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin, uuid7_default


class Goal(Base, TimestampMixin):
    __tablename__ = "goals"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid7_default
    )
    household_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("households.id", ondelete="CASCADE"), index=True
    )
    name: Mapped[str] = mapped_column(String(255))
    target_cents: Mapped[int] = mapped_column(BigInteger)
    current_cents: Mapped[int] = mapped_column(BigInteger, default=0)
    target_date: Mapped[date_type | None] = mapped_column(Date, nullable=True)
    icon: Mapped[str] = mapped_column(String(32))
    color: Mapped[str] = mapped_column(String(7))
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
