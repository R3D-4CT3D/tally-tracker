import uuid

from sqlalchemy import BigInteger, Boolean, ForeignKey, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin, uuid7_default


class Account(Base, TimestampMixin):
    __tablename__ = "accounts"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid7_default
    )
    household_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("households.id", ondelete="CASCADE"), index=True
    )
    name: Mapped[str] = mapped_column(String(255))
    type: Mapped[str] = mapped_column(String(20))
    institution: Mapped[str | None] = mapped_column(String(255), nullable=True)
    balance_cents: Mapped[int] = mapped_column(BigInteger, default=0)
    color: Mapped[str] = mapped_column(String(7))
    icon: Mapped[str] = mapped_column(String(32))
    archived: Mapped[bool] = mapped_column(Boolean, default=False)
