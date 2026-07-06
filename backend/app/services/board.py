import uuid
from datetime import UTC, date, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.checkin import Checkin
from app.models.debt import Debt
from app.models.financial_year_board import FinancialYearBoard
from app.models.goal import Goal
from app.models.streak import Streak
from app.schemas.board import BoardOut, BoardTileOut, StreakOut

BOARD_SIZE = 52
# Quarter/three-quarter marks, mirroring real Monopoly's 10-of-40 and
# 20-of-40 proportions -- flavor-only tiles, no logic attached to them.
JAIL_POSITION = 13
FREE_PARKING_POSITION = 39
COMMUNITY_CHEST_COUNT = 12  # ~monthly close cadence (52 weeks / ~4.33 weeks)
CHANCE_COUNT = 4
TAX_COUNT = 2
# "Get Out of Jail Free" cards, in the product's own vocabulary -- earn 1
# per 4 consecutive check-in weeks, bank max 2 at a time.
FREEZE_EARN_INTERVAL_WEEKS = 4
FREEZE_BANK_MAX = 2


def _iso_week_key(d: date) -> int:
    """iso_year * 100 + iso_week -- a single sortable, globally-unique
    integer across year boundaries (see Streak.last_checkin_week)."""
    iso_year, iso_week, _ = d.isocalendar()
    return iso_year * 100 + iso_week


def _week_key_to_monday(week_key: int) -> date:
    """Inverse of _iso_week_key -- the Monday of that ISO week, via
    date.fromisocalendar's exact ISO 8601 week-date arithmetic (handles
    52-vs-53-week years correctly, unlike naive integer math on the
    encoded key)."""
    iso_year, iso_week = divmod(week_key, 100)
    return date.fromisocalendar(iso_year, iso_week, 1)


def _weeks_between_keys(a: int, b: int) -> int:
    return (_week_key_to_monday(b) - _week_key_to_monday(a)).days // 7


def _spread_positions(count: int, taken: set[int]) -> list[int]:
    """Evenly spaces `count` positions around the 52-tile board, skipping
    tile 0 (GO) and any already-taken position by advancing to the next
    free slot. Deterministic given the same `taken` set and count.
    """
    positions: list[int] = []
    step = BOARD_SIZE / count
    cursor = 0.0
    for _ in range(count):
        pos = round(cursor) % BOARD_SIZE
        while pos == 0 or pos in taken or pos in positions:
            pos = (pos + 1) % BOARD_SIZE
        positions.append(pos)
        cursor += step
    return positions


async def get_or_create_active_board(
    db: AsyncSession, *, household_id: uuid.UUID
) -> FinancialYearBoard:
    """Loads the household's current board, creating one starting today if
    none exists at all, and performs lazy week reconciliation on every
    read (not a cron job, so the board is always correct whenever it's
    viewed regardless of whether a scheduled job has actually run):

    - Not yet finished: current_week is advanced to match how many full
      weeks have elapsed since year_start_date. If that reaches
      BOARD_SIZE, the board is marked completed_at=now right here --
      that's "passing GO" -- but this same (now-completed) row is still
      returned, not a fresh one.
    - Finished but tax_return_cents is still NULL: the year-end tax-return
      prompt hasn't been resolved yet (see record_tax_return) -- this
      finished board keeps being returned as-is so the frontend can keep
      showing the prompt across repeated fetches, rather than silently
      losing that state to an auto-created new board.
    - Finished and resolved (tax_return_cents set, possibly to 0 for "no
      return"): only now does a new board get created, starting today.
    """
    stmt = (
        select(FinancialYearBoard)
        .where(FinancialYearBoard.household_id == household_id)
        .order_by(FinancialYearBoard.year_start_date.desc())
        .limit(1)
    )
    result = await db.execute(stmt)
    board = result.scalar_one_or_none()

    today = datetime.now(UTC).date()
    if board is None:
        board = FinancialYearBoard(
            household_id=household_id, year_start_date=today, current_week=0
        )
        db.add(board)
        await db.flush()
        return board

    if board.completed_at is not None:
        if board.tax_return_cents is None:
            return board
        new_board = FinancialYearBoard(
            household_id=household_id, year_start_date=today, current_week=0
        )
        db.add(new_board)
        await db.flush()
        return new_board

    elapsed_weeks = (today - board.year_start_date).days // 7
    board.current_week = max(board.current_week, min(elapsed_weeks, BOARD_SIZE))
    if board.current_week >= BOARD_SIZE:
        board.completed_at = datetime.now(UTC)
    await db.flush()
    return board


async def record_tax_return(
    db: AsyncSession, *, household_id: uuid.UUID, amount_cents: int
) -> FinancialYearBoard | None:
    """Resolves a finished board's year-end tax-return prompt. amount_cents
    is 0 if the user declined ("no return this year") -- either way,
    setting it (even to 0, never leaving it NULL) is what tells
    get_or_create_active_board it's safe to start next year's board.
    Creating the actual income Transaction, if amount_cents > 0, is the
    API route's job (it needs an account_id, which this service has no
    opinion about) -- this function only finalizes the board row.
    """
    stmt = (
        select(FinancialYearBoard)
        .where(
            FinancialYearBoard.household_id == household_id,
            FinancialYearBoard.completed_at.isnot(None),
            FinancialYearBoard.tax_return_cents.is_(None),
        )
        .order_by(FinancialYearBoard.year_start_date.desc())
        .limit(1)
    )
    result = await db.execute(stmt)
    board = result.scalar_one_or_none()
    if board is None:
        return None
    board.tax_return_cents = amount_cents
    await db.flush()
    return board


async def get_or_create_streak(
    db: AsyncSession, *, household_id: uuid.UUID, user_id: uuid.UUID
) -> Streak:
    stmt = select(Streak).where(Streak.household_id == household_id, Streak.user_id == user_id)
    result = await db.execute(stmt)
    streak = result.scalar_one_or_none()
    if streak is None:
        streak = Streak(household_id=household_id, user_id=user_id)
        db.add(streak)
        await db.flush()
    return streak


async def record_checkin(
    db: AsyncSession, *, household_id: uuid.UUID, user_id: uuid.UUID, today: date | None = None
) -> Checkin:
    """Records that `user_id` did something meaningful this week (import,
    categorize, log a debt payment, contribute to a goal, complete a
    monthly close -- callers decide what counts, this just books it).

    Only the *first* check-in of a given ISO week updates streak
    bookkeeping -- subsequent check-ins in the same week just increment
    actions_count. A gap since the last check-in is covered by banked
    freezes if there are enough of them (streak continues, freezes spent);
    otherwise the streak resets to 1 rather than 0 (this check-in itself
    still counts).
    """
    resolved_today = today or datetime.now(UTC).date()
    week_key = _iso_week_key(resolved_today)

    stmt = select(Checkin).where(Checkin.user_id == user_id, Checkin.iso_week == week_key)
    result = await db.execute(stmt)
    checkin = result.scalar_one_or_none()
    is_first_checkin_this_week = checkin is None
    if checkin is None:
        checkin = Checkin(
            household_id=household_id, user_id=user_id, iso_week=week_key, actions_count=0
        )
        db.add(checkin)
    checkin.actions_count += 1

    if is_first_checkin_this_week:
        streak = await get_or_create_streak(db, household_id=household_id, user_id=user_id)
        if streak.last_checkin_week is None:
            streak.current_weeks = 1
        else:
            gap_weeks = _weeks_between_keys(streak.last_checkin_week, week_key) - 1
            if gap_weeks <= 0:
                streak.current_weeks += 1
            elif streak.freezes_banked >= gap_weeks:
                streak.freezes_banked -= gap_weeks
                streak.current_weeks += 1
            else:
                streak.current_weeks = 1
        streak.best_weeks = max(streak.best_weeks, streak.current_weeks)
        streak.last_checkin_week = week_key
        if streak.current_weeks % FREEZE_EARN_INTERVAL_WEEKS == 0:
            streak.freezes_banked = min(FREEZE_BANK_MAX, streak.freezes_banked + 1)

    await db.flush()
    return checkin


def _property_tile(index: int, goal: Goal, is_current: bool) -> BoardTileOut:
    return BoardTileOut(
        index=index,
        kind="property",
        label=goal.name,
        color=goal.color,
        icon=goal.icon,
        amount_cents=goal.target_cents,
        owned=goal.completed_at is not None,
        is_current=is_current,
        ref_id=str(goal.id),
    )


def _mortgage_tile(index: int, debt: Debt, is_current: bool) -> BoardTileOut:
    return BoardTileOut(
        index=index,
        kind="mortgage",
        label=debt.name,
        color=debt.color,
        icon=debt.icon,
        amount_cents=debt.current_balance_cents,
        owned=debt.paid_off_at is not None,
        is_current=is_current,
        ref_id=str(debt.id),
    )


async def compute_board_layout(
    db: AsyncSession, *, household_id: uuid.UUID, board: FinancialYearBoard
) -> list[BoardTileOut]:
    goals_result = await db.execute(
        select(Goal)
        .where(Goal.household_id == household_id)
        .order_by(Goal.created_at)
    )
    goals = list(goals_result.scalars().all())

    debts_result = await db.execute(
        select(Debt)
        .where(Debt.household_id == household_id, Debt.archived.is_(False))
        .order_by(Debt.created_at)
    )
    debts = list(debts_result.scalars().all())

    taken = {0, JAIL_POSITION, FREE_PARKING_POSITION}
    chest_positions = set(_spread_positions(COMMUNITY_CHEST_COUNT, taken))
    taken |= chest_positions
    chance_positions = set(_spread_positions(CHANCE_COUNT, taken))
    taken |= chance_positions
    tax_positions = set(_spread_positions(TAX_COUNT, taken))
    taken |= tax_positions

    entity_slots = [i for i in range(BOARD_SIZE) if i not in taken]
    entities: list[tuple[str, Goal | Debt]] = [("property", g) for g in goals] + [
        ("mortgage", d) for d in debts
    ]

    tiles: list[BoardTileOut] = []
    entity_idx = 0
    for index in range(BOARD_SIZE):
        is_current = index == board.current_week
        if index == 0:
            tiles.append(
                BoardTileOut(index=0, kind="go", label="GO", is_current=is_current)
            )
        elif index == JAIL_POSITION:
            tiles.append(
                BoardTileOut(index=index, kind="jail", label="Jail", is_current=is_current)
            )
        elif index == FREE_PARKING_POSITION:
            tiles.append(
                BoardTileOut(
                    index=index, kind="free_parking", label="Free Parking", is_current=is_current
                )
            )
        elif index in chest_positions:
            tiles.append(
                BoardTileOut(
                    index=index,
                    kind="chest",
                    label="Community Chest",
                    is_current=is_current,
                )
            )
        elif index in chance_positions:
            tiles.append(
                BoardTileOut(index=index, kind="chance", label="Chance", is_current=is_current)
            )
        elif index in tax_positions:
            tiles.append(
                BoardTileOut(index=index, kind="tax", label="Tax", is_current=is_current)
            )
        elif index in entity_slots and entity_idx < len(entities):
            kind, entity = entities[entity_idx]
            entity_idx += 1
            if kind == "property":
                tiles.append(_property_tile(index, entity, is_current))  # type: ignore[arg-type]
            else:
                tiles.append(_mortgage_tile(index, entity, is_current))  # type: ignore[arg-type]
        else:
            tiles.append(
                BoardTileOut(
                    index=index, kind="plain", label=f"Week {index}", is_current=is_current
                )
            )
    return tiles


async def get_board(db: AsyncSession, *, household_id: uuid.UUID, user_id: uuid.UUID) -> BoardOut:
    board = await get_or_create_active_board(db, household_id=household_id)
    tiles = await compute_board_layout(db, household_id=household_id, board=board)
    streak = await get_or_create_streak(db, household_id=household_id, user_id=user_id)
    return BoardOut(
        year_start_date=board.year_start_date,
        current_week=board.current_week,
        board_size=BOARD_SIZE,
        tiles=tiles,
        streak=StreakOut(
            current_weeks=streak.current_weeks,
            best_weeks=streak.best_weeks,
            freezes_banked=streak.freezes_banked,
        ),
        year_end_pending=board.completed_at is not None and board.tax_return_cents is None,
    )
