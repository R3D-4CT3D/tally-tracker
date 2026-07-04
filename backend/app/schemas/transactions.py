from datetime import date as date_type
from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class TransactionCreate(BaseModel):
    account_id: UUID
    date: date_type
    amount_cents: int
    description: str = Field(min_length=1, max_length=500)
    category_id: UUID | None = None
    notes: str | None = Field(default=None, max_length=5000)


class TransactionUpdate(BaseModel):
    """Fields are only applied if present in the request body at all --
    services/transactions.py uses `model_dump(exclude_unset=True)`, so an
    explicit `"category_id": null` clears the category, while omitting the
    field entirely leaves it untouched. A plain `Optional[...] = None`
    default alone can't distinguish those two cases.
    """

    account_id: UUID | None = None
    date: date_type | None = None
    amount_cents: int | None = None
    description: str | None = Field(default=None, min_length=1, max_length=500)
    category_id: UUID | None = None
    notes: str | None = Field(default=None, max_length=5000)


class TransactionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    account_id: UUID
    date: date_type
    amount_cents: int
    description_raw: str
    description_display: str
    category_id: UUID | None
    notes: str | None
    source: str
    created_by: UUID
    created_at: datetime
    updated_at: datetime


class TransactionListParams(BaseModel):
    date_from: date_type | None = None
    date_to: date_type | None = None
    account_id: UUID | None = None
    category_id: UUID | None = None
    uncategorized: bool = False
    search: str | None = Field(default=None, max_length=200)
    cursor: str | None = None
    limit: int = Field(default=25, ge=1, le=100)


class TransactionListResponse(BaseModel):
    items: list[TransactionOut]
    next_cursor: str | None
