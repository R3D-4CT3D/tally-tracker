from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

MatchType = Literal["contains", "starts_with", "regex"]


class RuleCreate(BaseModel):
    priority: int | None = None
    match_type: MatchType
    match_value: str = Field(min_length=1, max_length=200)
    amount_min: int | None = None
    amount_max: int | None = None
    account_id: UUID | None = None
    set_category_id: UUID
    set_display_name: str | None = Field(default=None, max_length=500)
    enabled: bool = True


class RuleUpdate(BaseModel):
    """Fields are only applied if present in the request body at all -- see
    app/services/rules.py's `model_dump(exclude_unset=True)` usage, same
    pattern as M2's category/transaction updates.
    """

    priority: int | None = None
    match_type: MatchType | None = None
    match_value: str | None = Field(default=None, min_length=1, max_length=200)
    amount_min: int | None = None
    amount_max: int | None = None
    account_id: UUID | None = None
    set_category_id: UUID | None = None
    set_display_name: str | None = Field(default=None, max_length=500)
    enabled: bool | None = None


class RuleOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    priority: int
    match_type: str
    match_value: str
    amount_min: int | None
    amount_max: int | None
    account_id: UUID | None
    set_category_id: UUID
    set_display_name: str | None
    enabled: bool
    created_at: datetime
    updated_at: datetime


class RuleReorderRequest(BaseModel):
    ordered_ids: list[UUID]
