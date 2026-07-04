import uuid
from typing import Any

from sqlalchemy import ForeignKey, String
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin, uuid7_default


class ImportProfile(Base, TimestampMixin):
    """A saved column mapping for a CSV source (e.g. "Chase Checking") --
    describes the file *format*, not a specific account. account_id is
    chosen fresh on every import (see docs/TALLY_BUILD_SPEC.md §5's schema,
    which likewise has no account_id column here).
    """

    __tablename__ = "import_profiles"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid7_default
    )
    household_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("households.id", ondelete="CASCADE"), index=True
    )
    name: Mapped[str] = mapped_column(String(100))
    column_mapping: Mapped[dict[str, Any]] = mapped_column(JSONB)
    date_format: Mapped[str] = mapped_column(String(10))
    source_hint: Mapped[str | None] = mapped_column(String(100), nullable=True)
