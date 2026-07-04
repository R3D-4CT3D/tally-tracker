import uuid
from datetime import date as date_type

from sqlalchemy import BigInteger, Date, ForeignKey, Index, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin, uuid7_default


class Transaction(Base, TimestampMixin):
    __tablename__ = "transactions"
    __table_args__ = (
        UniqueConstraint("household_id", "dedupe_hash"),
        # Explicit names: the Base metadata naming convention keys "ix" off
        # column_0_label only, which would collide across all three of these
        # (they all start with household_id).
        Index("ix_transactions_household_date", "household_id", "date"),
        Index("ix_transactions_household_category", "household_id", "category_id"),
        Index("ix_transactions_household_account", "household_id", "account_id"),
        Index("ix_transactions_import_batch", "import_batch_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid7_default
    )
    household_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("households.id", ondelete="CASCADE"))
    account_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("accounts.id", ondelete="CASCADE"))
    date: Mapped[date_type] = mapped_column(Date)
    amount_cents: Mapped[int] = mapped_column(BigInteger)
    description_raw: Mapped[str] = mapped_column(String(500))
    description_display: Mapped[str] = mapped_column(String(500))
    category_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("categories.id", ondelete="SET NULL"), nullable=True
    )
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    source: Mapped[str] = mapped_column(String(20), default="manual")
    dedupe_hash: Mapped[str] = mapped_column(String(64))
    created_by: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"))
    import_batch_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("import_batches.id", ondelete="CASCADE"), nullable=True
    )
