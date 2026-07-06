from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

DateFormat = Literal["MDY", "DMY", "YMD"]


class ColumnMapping(BaseModel):
    date: str
    description: str
    amount: str
    # Optional, defaults to `description` when unset: some bank exports (e.g.
    # Wells Fargo credit card) want a clean display description but a
    # separate raw-merchant column for dedupe hashing, since the display
    # text alone is too generic/repeated to dedupe reliably against.
    dedupe_description: str | None = None


class ImportUploadResponse(BaseModel):
    import_session_id: str
    filename: str | None
    source: Literal["csv", "paste"]
    header: list[str]
    sample_rows: list[list[str]]
    row_count: int
    suggested_mapping: ColumnMapping | None
    date_format_suggestion: DateFormat
    date_format_ambiguous: bool
    # True when the format is already known for certain -- either an
    # explicit saved profile was selected, or the header matched a built-in
    # bank-format signature (app/services/bank_formats.py). The wizard skips
    # the manual column-mapping step entirely in either case.
    skip_mapping_step: bool = False
    detected_bank_format: str | None = None
    suggested_account_id: UUID | None = None


class ImportPasteRequest(BaseModel):
    text: str = Field(min_length=1)
    profile_id: UUID | None = None


class ImportPreviewRequest(BaseModel):
    column_mapping: ColumnMapping
    date_format: DateFormat
    account_id: UUID


class ImportPreviewRow(BaseModel):
    row_index: int
    date: str | None
    description: str | None
    description_display: str | None
    amount_cents: int | None
    category_id: UUID | None
    matched_rule_id: UUID | None
    duplicate: Literal["exact", "fuzzy"] | None
    error: str | None
    will_import: bool


class ImportPreviewResponse(BaseModel):
    rows: list[ImportPreviewRow]
    valid_count: int
    error_count: int
    exact_duplicate_count: int
    fuzzy_duplicate_count: int


class ImportCommitRequest(BaseModel):
    column_mapping: ColumnMapping
    date_format: DateFormat
    account_id: UUID
    # Keyed by row_index (as a string -- JSON object keys are always
    # strings): True = include this row even though the default decision
    # would skip it (an exact duplicate); False = skip a row that would
    # otherwise default to included. Rows with a parse error are always
    # excluded regardless of what's in here.
    overrides: dict[str, bool] = Field(default_factory=dict)
    source_profile_id: UUID | None = None
    save_profile_name: str | None = Field(default=None, min_length=1, max_length=100)


class ImportBatchOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    filename: str | None
    row_count: int
    imported_count: int
    skipped_dupes: int
    auto_categorized_count: int
    created_at: datetime
    undoable: bool
