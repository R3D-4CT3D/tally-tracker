from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

DebtType = Literal["credit_card", "auto_loan", "student_loan", "personal"]


class DebtCreate(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    type: DebtType
    original_balance_cents: int = Field(ge=0)
    current_balance_cents: int = Field(ge=0)
    apr_bps: int = Field(ge=0)
    min_payment_cents: int = Field(ge=0)
    due_day: int = Field(ge=1, le=31)


class DebtUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=255)
    type: DebtType | None = None
    original_balance_cents: int | None = Field(default=None, ge=0)
    current_balance_cents: int | None = Field(default=None, ge=0)
    apr_bps: int | None = Field(default=None, ge=0)
    min_payment_cents: int | None = Field(default=None, ge=0)
    due_day: int | None = Field(default=None, ge=1, le=31)


class DebtOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    type: str
    original_balance_cents: int
    current_balance_cents: int
    apr_bps: int
    min_payment_cents: int
    due_day: int
    paid_off_at: datetime | None
    archived: bool
    created_at: datetime
    updated_at: datetime
