import uuid

from sqlalchemy import BigInteger, Boolean, ForeignKey, Index, Integer, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin, uuid7_default


class Rule(Base, TimestampMixin):
    """IF description matches (contains/starts_with/regex) AND optional
    amount range/account THEN set category [and rename display
    description]. Evaluated in `priority` order (ascending, lower = first),
    first match wins -- see app/services/rules.py.
    """

    __tablename__ = "rules"
    __table_args__ = (Index("ix_rules_household_priority", "household_id", "priority"),)

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid7_default
    )
    household_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("households.id", ondelete="CASCADE")
    )
    priority: Mapped[int] = mapped_column(Integer)
    match_type: Mapped[str] = mapped_column(String(20))
    match_value: Mapped[str] = mapped_column(String(200))
    amount_min: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    amount_max: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    account_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("accounts.id", ondelete="SET NULL"), nullable=True
    )
    set_category_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("categories.id"))
    set_display_name: Mapped[str | None] = mapped_column(String(500), nullable=True)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)
