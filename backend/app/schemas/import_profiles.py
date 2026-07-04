from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.imports import ColumnMapping, DateFormat


class ImportProfileCreate(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    column_mapping: ColumnMapping
    date_format: DateFormat
    source_hint: str | None = Field(default=None, max_length=100)


class ImportProfileOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    column_mapping: ColumnMapping
    date_format: str
    source_hint: str | None
    created_at: datetime
    updated_at: datetime
