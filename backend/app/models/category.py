import uuid

from sqlalchemy import Boolean, ForeignKey, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin, uuid7_default


class Category(Base, TimestampMixin):
    """No DB-level uniqueness on (household_id, name) -- see M2 plan's note
    on why a nullable parent_id makes a partial index the only reliable way
    to enforce that, which isn't worth it for a "you can see the list before
    creating" UX problem.
    """

    __tablename__ = "categories"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid7_default
    )
    household_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("households.id", ondelete="CASCADE"), index=True
    )
    name: Mapped[str] = mapped_column(String(100))
    # One level of subcategories max -- enforced in app/services/categories.py,
    # not the DB (a CHECK constraint can't reach across rows to see whether
    # parent_id's own parent_id is set).
    parent_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("categories.id", ondelete="SET NULL"), nullable=True
    )
    icon: Mapped[str] = mapped_column(String(32))
    color: Mapped[str] = mapped_column(String(7))
    is_system: Mapped[bool] = mapped_column(Boolean, default=False)
