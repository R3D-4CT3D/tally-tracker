from datetime import date as date_type
from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict

Grade = Literal["A", "B", "C", "D"]


class MonthlyCloseSnapshot(BaseModel):
    """The computed 6-step recap. Persisted verbatim into
    MonthlyClose.snapshot (JSONB) at completion time so re-viewing a past
    close shows what was true *then*, not a recomputation against
    since-changed live data -- but this same shape is also what the
    not-yet-persisted preview endpoint returns, so the wizard and the
    history view render identically.
    """

    uncategorized_count: int
    income_cents: int
    spend_cents: int
    prior_income_cents: int | None
    prior_spend_cents: int | None
    debt_payments_cents: int
    total_debt_cents: int
    start_of_month_debt_cents: int | None
    goal_contributions_cents: int
    goals_completed: list[str]
    net_worth_cents: int | None
    prior_net_worth_cents: int | None
    grade: Grade
    highlight: str


class MonthlyCloseOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    month: date_type
    completed_by: UUID
    completed_at: datetime
    grade: Grade
    snapshot: MonthlyCloseSnapshot


class CompleteMonthlyCloseRequest(BaseModel):
    month: date_type
