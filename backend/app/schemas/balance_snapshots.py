from datetime import date as date_type
from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class BalanceSnapshotOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    date: date_type
    cash_cents: int
    debt_cents: int
    created_at: datetime
    updated_at: datetime


class BalanceSnapshotListParams(BaseModel):
    date_from: date_type | None = None
    date_to: date_type | None = None
    limit: int = Field(default=90, ge=1, le=366)
