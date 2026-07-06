from datetime import date as date_type
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field, model_validator

TileKind = Literal[
    "go", "property", "mortgage", "chest", "chance", "tax", "jail", "free_parking", "plain"
]


class BoardTileOut(BaseModel):
    index: int
    kind: TileKind
    label: str
    color: str | None = None
    icon: str | None = None
    amount_cents: int | None = None
    # True once the underlying Goal/Debt is settled (Goal.completed_at set /
    # Debt.paid_off_at set) -- meaningless for non-property/mortgage tiles.
    owned: bool = False
    is_current: bool = False
    ref_id: str | None = None


class StreakOut(BaseModel):
    current_weeks: int
    best_weeks: int
    freezes_banked: int


class BoardOut(BaseModel):
    year_start_date: date_type
    current_week: int
    board_size: int
    tiles: list[BoardTileOut]
    streak: StreakOut
    # True once current_week has reached board_size and the year-end
    # tax-return prompt hasn't been resolved yet (see record_tax_return) --
    # tells the frontend to show the passing-GO animation + prompt instead
    # of the normal board.
    year_end_pending: bool = False


class TaxReturnRequest(BaseModel):
    """account_id is required when amount_cents > 0 (the income transaction
    needs somewhere to land) and ignored when declining (amount_cents=0)."""

    account_id: UUID | None = None
    amount_cents: int = Field(ge=0)

    @model_validator(mode="after")
    def _account_required_when_amount_positive(self) -> "TaxReturnRequest":
        if self.amount_cents > 0 and self.account_id is None:
            raise ValueError("account_id is required when amount_cents > 0")
        return self
