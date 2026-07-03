import uuid
from datetime import UTC, datetime

from sqlalchemy import DateTime, MetaData
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from uuid6 import uuid7

# Explicit naming convention so Alembic autogenerate produces stable, diffable
# constraint names instead of database-assigned defaults that vary by backend.
NAMING_CONVENTION = {
    "ix": "ix_%(column_0_label)s",
    "uq": "uq_%(table_name)s_%(column_0_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
}


class Base(DeclarativeBase):
    metadata = MetaData(naming_convention=NAMING_CONVENTION)


class TimestampMixin:
    """created_at/updated_at columns shared by every table per docs/spec.md §5."""

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
    )


def uuid7_default() -> uuid.UUID:
    """Default factory for UUIDv7 primary keys.

    Postgres 16 has no native uuidv7() function, so IDs are generated
    application-side via the pure-Python `uuid6` package — chosen over
    C-extension alternatives for arm64/Raspberry Pi wheel availability.
    See docs/adr/0002-tooling-choices.md.
    """
    return uuid7()
