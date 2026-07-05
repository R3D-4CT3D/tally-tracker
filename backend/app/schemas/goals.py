from datetime import date as date_type
from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

_COLOR_PATTERN = r"^#[0-9a-fA-F]{6}$"


class GoalCreate(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    target_cents: int = Field(gt=0)
    current_cents: int = Field(default=0, ge=0)
    target_date: date_type | None = None
    icon: str = Field(min_length=1, max_length=32)
    color: str = Field(pattern=_COLOR_PATTERN)


class GoalUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=255)
    target_cents: int | None = Field(default=None, gt=0)
    target_date: date_type | None = None
    icon: str | None = Field(default=None, min_length=1, max_length=32)
    color: str | None = Field(default=None, pattern=_COLOR_PATTERN)


class GoalOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    target_cents: int
    current_cents: int
    target_date: date_type | None
    icon: str
    color: str
    completed_at: datetime | None
    created_at: datetime
    updated_at: datetime


class GoalContributionCreate(BaseModel):
    amount_cents: int
    date: date_type
    transaction_id: UUID | None = None


class GoalContributionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    goal_id: UUID
    transaction_id: UUID | None
    amount_cents: int
    date: date_type
    user_id: UUID
    created_at: datetime
    updated_at: datetime
