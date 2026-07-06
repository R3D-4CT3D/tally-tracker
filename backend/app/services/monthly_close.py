import calendar
import uuid
from datetime import UTC, date, datetime

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.balance_snapshot import BalanceSnapshot
from app.models.debt import Debt
from app.models.goal import Goal
from app.models.goal_contribution import GoalContribution
from app.models.monthly_close import MonthlyClose
from app.models.transaction import Transaction
from app.schemas.monthly_close import Grade, MonthlyCloseSnapshot


def _month_bounds(month: date) -> tuple[date, date]:
    """First and last calendar day of `month`'s month, regardless of what
    day-of-month `month` itself is (callers pass the 1st by convention, but
    this doesn't require it)."""
    first_day = month.replace(day=1)
    last_day = month.replace(day=calendar.monthrange(month.year, month.month)[1])
    return first_day, last_day


def _previous_month(month: date) -> date:
    first_day = month.replace(day=1)
    if first_day.month == 1:
        return first_day.replace(year=first_day.year - 1, month=12)
    return first_day.replace(month=first_day.month - 1)


def _compute_grade(
    *,
    debt_payments_cents: int,
    total_min_payments_cents: int,
    spend_cents: int,
    prior_spend_cents: int | None,
    goal_contributions_cents: int,
    has_active_goals: bool,
    net_worth_cents: int | None,
    prior_net_worth_cents: int | None,
) -> Grade:
    """v0 formula (spec: "ship a v0 formula behind a single tunable
    function") -- a simple weighted score of debt paydown vs. minimums,
    spend trend, and savings rate, since this app has no budget-setting
    feature to check "budget adherence" against directly. Never below D,
    copy stays kind (see docs/product-principles.md) -- a criterion with no
    data to judge (no debts, no goals, no prior month) counts as a pass
    rather than a penalty.
    """
    score = 0
    score += (
        1 if total_min_payments_cents == 0 or debt_payments_cents >= total_min_payments_cents else 0
    )
    score += 1 if prior_spend_cents is None or spend_cents <= prior_spend_cents * 1.05 else 0
    score += 1 if not has_active_goals or goal_contributions_cents > 0 else 0
    score += (
        1
        if net_worth_cents is None
        or prior_net_worth_cents is None
        or net_worth_cents >= prior_net_worth_cents
        else 0
    )

    if score >= 4:
        return "A"
    if score == 3:
        return "B"
    if score == 2:
        return "C"
    return "D"


def _highlight(
    *, debt_payments_cents: int, goal_contributions_cents: int, goals_completed: list[str]
) -> str:
    if goals_completed:
        return f'You reached your "{goals_completed[0]}" goal this month!'
    if debt_payments_cents > 0 and debt_payments_cents >= goal_contributions_cents:
        return f"You paid down ${debt_payments_cents / 100:,.2f} in debt this month."
    if goal_contributions_cents > 0:
        return f"You put ${goal_contributions_cents / 100:,.2f} toward your goals this month."
    return "You showed up and kept your ledger honest this month -- that's the whole game."


async def compute_monthly_close_snapshot(
    db: AsyncSession, *, household_id: uuid.UUID, month: date
) -> MonthlyCloseSnapshot:
    """Computed fresh every call -- not persisted here (see
    complete_monthly_close for that). Used both by the preview endpoint
    (wizard steps 1-5, before the user commits) and to build the snapshot
    actually saved at completion time."""
    first_day, last_day = _month_bounds(month)
    prior_first_day, prior_last_day = _month_bounds(_previous_month(month))

    uncategorized_count = (
        await db.execute(
            select(func.count())
            .select_from(Transaction)
            .where(
                Transaction.household_id == household_id,
                Transaction.date >= first_day,
                Transaction.date <= last_day,
                Transaction.category_id.is_(None),
            )
        )
    ).scalar_one()

    async def _income_and_spend(start: date, end: date) -> tuple[int, int]:
        income = (
            await db.execute(
                select(func.coalesce(func.sum(Transaction.amount_cents), 0)).where(
                    Transaction.household_id == household_id,
                    Transaction.date >= start,
                    Transaction.date <= end,
                    Transaction.amount_cents > 0,
                )
            )
        ).scalar_one()
        spend = (
            await db.execute(
                select(func.coalesce(func.sum(Transaction.amount_cents), 0)).where(
                    Transaction.household_id == household_id,
                    Transaction.date >= start,
                    Transaction.date <= end,
                    Transaction.amount_cents < 0,
                )
            )
        ).scalar_one()
        return int(income), int(-spend)

    income_cents, spend_cents = await _income_and_spend(first_day, last_day)
    prior_income_cents, prior_spend_cents = await _income_and_spend(prior_first_day, prior_last_day)
    has_prior_month_data = prior_income_cents > 0 or prior_spend_cents > 0

    debt_payments_cents = int(
        (
            await db.execute(
                select(func.coalesce(func.sum(-Transaction.amount_cents), 0)).where(
                    Transaction.household_id == household_id,
                    Transaction.date >= first_day,
                    Transaction.date <= last_day,
                    Transaction.debt_id.isnot(None),
                    Transaction.amount_cents < 0,
                )
            )
        ).scalar_one()
    )

    debts = list(
        (
            await db.execute(
                select(Debt).where(Debt.household_id == household_id, Debt.archived.is_(False))
            )
        )
        .scalars()
        .all()
    )
    total_debt_cents = sum(d.current_balance_cents for d in debts)
    total_min_payments_cents = sum(d.min_payment_cents for d in debts)

    start_of_month_snapshot = (
        await db.execute(
            select(BalanceSnapshot)
            .where(BalanceSnapshot.household_id == household_id, BalanceSnapshot.date < first_day)
            .order_by(BalanceSnapshot.date.desc())
            .limit(1)
        )
    ).scalar_one_or_none()
    start_of_month_debt_cents = (
        start_of_month_snapshot.debt_cents if start_of_month_snapshot is not None else None
    )

    latest_snapshot = (
        await db.execute(
            select(BalanceSnapshot)
            .where(BalanceSnapshot.household_id == household_id, BalanceSnapshot.date <= last_day)
            .order_by(BalanceSnapshot.date.desc())
            .limit(1)
        )
    ).scalar_one_or_none()
    net_worth_cents = (
        latest_snapshot.cash_cents - latest_snapshot.debt_cents
        if latest_snapshot is not None
        else None
    )
    prior_net_worth_cents = (
        start_of_month_snapshot.cash_cents - start_of_month_snapshot.debt_cents
        if start_of_month_snapshot is not None
        else None
    )

    goal_contributions_cents = int(
        (
            await db.execute(
                select(func.coalesce(func.sum(GoalContribution.amount_cents), 0)).where(
                    GoalContribution.household_id == household_id,
                    GoalContribution.date >= first_day,
                    GoalContribution.date <= last_day,
                )
            )
        ).scalar_one()
    )

    goals_completed_this_month = list(
        (
            await db.execute(
                select(Goal.name).where(
                    Goal.household_id == household_id,
                    Goal.completed_at.isnot(None),
                    Goal.completed_at
                    >= datetime.combine(first_day, datetime.min.time(), tzinfo=UTC),
                    Goal.completed_at
                    <= datetime.combine(last_day, datetime.max.time(), tzinfo=UTC),
                )
            )
        )
        .scalars()
        .all()
    )

    has_active_goals = (
        await db.execute(
            select(func.count())
            .select_from(Goal)
            .where(Goal.household_id == household_id, Goal.completed_at.is_(None))
        )
    ).scalar_one() > 0

    grade = _compute_grade(
        debt_payments_cents=debt_payments_cents,
        total_min_payments_cents=total_min_payments_cents,
        spend_cents=spend_cents,
        prior_spend_cents=prior_spend_cents if has_prior_month_data else None,
        goal_contributions_cents=goal_contributions_cents,
        has_active_goals=has_active_goals,
        net_worth_cents=net_worth_cents,
        prior_net_worth_cents=prior_net_worth_cents,
    )
    highlight = _highlight(
        debt_payments_cents=debt_payments_cents,
        goal_contributions_cents=goal_contributions_cents,
        goals_completed=goals_completed_this_month,
    )

    return MonthlyCloseSnapshot(
        uncategorized_count=uncategorized_count,
        income_cents=income_cents,
        spend_cents=spend_cents,
        prior_income_cents=prior_income_cents if has_prior_month_data else None,
        prior_spend_cents=prior_spend_cents if has_prior_month_data else None,
        debt_payments_cents=debt_payments_cents,
        total_debt_cents=total_debt_cents,
        start_of_month_debt_cents=start_of_month_debt_cents,
        goal_contributions_cents=goal_contributions_cents,
        goals_completed=goals_completed_this_month,
        net_worth_cents=net_worth_cents,
        prior_net_worth_cents=prior_net_worth_cents,
        grade=grade,
        highlight=highlight,
    )


async def get_monthly_close(
    db: AsyncSession, *, household_id: uuid.UUID, month: date
) -> MonthlyClose | None:
    first_day, _ = _month_bounds(month)
    stmt = select(MonthlyClose).where(
        MonthlyClose.household_id == household_id, MonthlyClose.month == first_day
    )
    result = await db.execute(stmt)
    return result.scalar_one_or_none()


async def list_monthly_closes(db: AsyncSession, *, household_id: uuid.UUID) -> list[MonthlyClose]:
    stmt = (
        select(MonthlyClose)
        .where(MonthlyClose.household_id == household_id)
        .order_by(MonthlyClose.month.desc())
    )
    result = await db.execute(stmt)
    return list(result.scalars().all())


async def complete_monthly_close(
    db: AsyncSession, *, household_id: uuid.UUID, month: date, completed_by: uuid.UUID
) -> MonthlyClose:
    """Idempotent per (household, month): completing an already-closed
    month overwrites it with a freshly computed snapshot/grade rather than
    erroring -- there's no reason a household couldn't want to re-run the
    ceremony after fixing a miscategorized transaction, and the unique
    constraint on (household_id, month) means there's only ever one row to
    update either way.
    """
    first_day, _ = _month_bounds(month)
    snapshot = await compute_monthly_close_snapshot(db, household_id=household_id, month=first_day)

    existing = await get_monthly_close(db, household_id=household_id, month=first_day)
    if existing is not None:
        existing.completed_by = completed_by
        existing.completed_at = datetime.now(UTC)
        existing.grade = snapshot.grade
        existing.snapshot = snapshot.model_dump(mode="json")
        await db.flush()
        return existing

    monthly_close = MonthlyClose(
        household_id=household_id,
        month=first_day,
        completed_by=completed_by,
        completed_at=datetime.now(UTC),
        grade=snapshot.grade,
        snapshot=snapshot.model_dump(mode="json"),
    )
    db.add(monthly_close)
    await db.flush()
    return monthly_close
