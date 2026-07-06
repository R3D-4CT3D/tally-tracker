from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

AccountType = Literal["checking", "savings", "credit_card", "loan", "cash"]

_COLOR_PATTERN = r"^#[0-9a-fA-F]{6}$"


_LAST_FOUR_PATTERN = r"^[0-9]{4}$"


class AccountCreate(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    type: AccountType
    institution: str | None = Field(default=None, max_length=255)
    balance_cents: int = 0
    color: str = Field(pattern=_COLOR_PATTERN)
    icon: str = Field(min_length=1, max_length=32)
    last_four: str | None = Field(default=None, pattern=_LAST_FOUR_PATTERN)


class AccountUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=255)
    type: AccountType | None = None
    institution: str | None = Field(default=None, max_length=255)
    balance_cents: int | None = None
    color: str | None = Field(default=None, pattern=_COLOR_PATTERN)
    icon: str | None = Field(default=None, min_length=1, max_length=32)
    last_four: str | None = Field(default=None, pattern=_LAST_FOUR_PATTERN)


class AccountOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    type: str
    institution: str | None
    balance_cents: int
    color: str
    icon: str
    archived: bool
    last_four: str | None
    created_at: datetime
    updated_at: datetime
