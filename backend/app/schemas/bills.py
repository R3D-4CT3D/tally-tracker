from datetime import date as date_type
from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

BillFrequency = Literal["monthly", "quarterly", "annual", "custom"]
BillPaymentStatus = Literal["pending", "paid", "skipped"]


class BillCreate(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    amount_cents: int | None = Field(default=None, ge=0)
    is_variable: bool = False
    frequency: BillFrequency
    due_day: int = Field(ge=1, le=31)
    custom_interval_days: int | None = Field(default=None, ge=1)
    account_id: UUID | None = None
    category_id: UUID | None = None
    autopay: bool = False
    next_due_date: date_type


class BillUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=255)
    amount_cents: int | None = Field(default=None, ge=0)
    is_variable: bool | None = None
    frequency: BillFrequency | None = None
    due_day: int | None = Field(default=None, ge=1, le=31)
    custom_interval_days: int | None = Field(default=None, ge=1)
    account_id: UUID | None = None
    category_id: UUID | None = None
    autopay: bool | None = None
    next_due_date: date_type | None = None


class BillOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    amount_cents: int | None
    is_variable: bool
    frequency: str
    due_day: int
    custom_interval_days: int | None
    account_id: UUID | None
    category_id: UUID | None
    autopay: bool
    next_due_date: date_type
    archived: bool
    created_at: datetime
    updated_at: datetime


class BillMarkPaidRequest(BaseModel):
    """Link-first with quick-create fallback (see docs/TALLY_BUILD_SPEC.md
    §10's open-item recommendation). Exactly one of `transaction_id` (link an
    existing transaction) or the quick-create fields (account_id/amount_cents
    /date) must be present -- validated in app/services/bill_payments.py, not
    via a Pydantic discriminated union, since it's a one-of-these-present
    check rather than a fixed enum tag.
    """

    transaction_id: UUID | None = None
    account_id: UUID | None = None
    amount_cents: int | None = None
    date: date_type | None = None
    category_id: UUID | None = None
    notes: str | None = Field(default=None, max_length=5000)


class BillPaymentOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    bill_id: UUID
    transaction_id: UUID | None
    due_date: date_type
    paid_date: date_type | None
    amount_cents: int
    status: str
    created_at: datetime
    updated_at: datetime
