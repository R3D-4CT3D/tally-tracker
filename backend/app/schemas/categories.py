from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

_COLOR_PATTERN = r"^#[0-9a-fA-F]{6}$"


class CategoryCreate(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    parent_id: UUID | None = None
    icon: str = Field(min_length=1, max_length=32)
    color: str = Field(pattern=_COLOR_PATTERN)


class CategoryUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=100)
    parent_id: UUID | None = None
    icon: str | None = Field(default=None, min_length=1, max_length=32)
    color: str | None = Field(default=None, pattern=_COLOR_PATTERN)


class CategoryOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    parent_id: UUID | None
    icon: str
    color: str
    is_system: bool
    created_at: datetime
    updated_at: datetime
