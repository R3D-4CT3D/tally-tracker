import uuid

from sqlalchemy import ForeignKey, Integer, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin, uuid7_default


class ImportBatch(Base, TimestampMixin):
    """One commit of the import pipeline (CSV or paste). Deleting this row
    cascades to delete every transaction it created (see
    Transaction.import_batch_id's ON DELETE CASCADE) -- that's the entire
    mechanism behind "undo a batch wholesale within 24h": one DELETE here,
    the database does the rest atomically.
    """

    __tablename__ = "import_batches"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid7_default
    )
    household_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("households.id", ondelete="CASCADE"), index=True
    )
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"))
    source_profile_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("import_profiles.id", ondelete="SET NULL"), nullable=True
    )
    filename: Mapped[str | None] = mapped_column(String(255), nullable=True)
    row_count: Mapped[int] = mapped_column(Integer)
    imported_count: Mapped[int] = mapped_column(Integer)
    skipped_dupes: Mapped[int] = mapped_column(Integer)
    # Committed rows where a rule (user-defined or built-in merchant pattern)
    # set the category -- surfaced in the wizard's post-commit summary.
    auto_categorized_count: Mapped[int] = mapped_column(Integer, default=0)
