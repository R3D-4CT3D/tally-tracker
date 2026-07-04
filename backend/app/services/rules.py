import logging
import uuid

import regex
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.rule import Rule
from app.schemas.rules import RuleCreate, RuleUpdate
from app.services.accounts import get_account
from app.services.categories import get_category
from app.services.transactions import InvalidReferenceError

logger = logging.getLogger(__name__)

_MAX_REGEX_LENGTH = 200


class RuleError(Exception):
    """Invalid rule definition -- bad match_type, invalid/oversized regex, or
    a reorder call whose id set doesn't match the household's actual rules.
    """


def _validate_match_pattern(match_type: str, match_value: str) -> None:
    if match_type not in ("contains", "starts_with", "regex"):
        raise RuleError(f"Unknown match_type: {match_type!r}")
    if match_type == "regex":
        if len(match_value) > _MAX_REGEX_LENGTH:
            raise RuleError("Regex pattern is too long")
        try:
            regex.compile(match_value)
        except regex.error as exc:
            raise RuleError(f"Invalid regex pattern: {exc}") from exc


def _regex_search_with_timeout(pattern: str, text: str, timeout: float) -> bool:
    """ReDoS defense: a hard wall-clock timeout, not a static "reject this
    shape" heuristic -- static nested-quantifier detection is incomplete
    (misses many catastrophic shapes) and risks false positives on
    legitimate patterns.

    Two stdlib-only approaches were tried and rejected before this, each
    confirmed broken by actually running a catastrophic pattern
    (`(a|a)+$`) against it, not just reasoned about:

    1. A shared `concurrent.futures.ThreadPoolExecutor`: worker threads are
       non-daemon, so a single catastrophic match permanently occupies one
       of the pool's few workers forever (Python threads can't be killed),
       and the interpreter hangs at shutdown joining that stuck worker.
    2. A fresh `daemon=True` thread per call: fixes the shutdown hang, but
       CPython's `_sre` C matcher does not release the GIL mid-match, so
       the *main* thread's `Thread.join(timeout=...)` can't actually wake
       up and resume Python bytecode within its timeout window either --
       it wound up blocking for the runaway match's entire real duration
       regardless of the timeout argument.

    The third-party `regex` package (a very widely used, actively
    maintained `re` superset with prebuilt wheels across platforms
    including arm64) checks elapsed time cooperatively *inside* its own
    matching loop and raises `TimeoutError` -- no second thread/process
    involved, so there's nothing for the GIL to starve and nothing to leak.
    """
    try:
        return regex.search(pattern, text, regex.IGNORECASE, timeout=timeout) is not None
    except TimeoutError:
        logger.warning("Rule regex match timed out (possible ReDoS pattern): %r", pattern)
        return False


def evaluate_rule(
    rule: Rule,
    *,
    description: str,
    amount_cents: int,
    account_id: uuid.UUID,
    timeout: float,
) -> bool:
    if rule.account_id is not None and rule.account_id != account_id:
        return False
    if rule.amount_min is not None and amount_cents < rule.amount_min:
        return False
    if rule.amount_max is not None and amount_cents > rule.amount_max:
        return False

    if rule.match_type == "contains":
        return rule.match_value.lower() in description.lower()
    if rule.match_type == "starts_with":
        return description.lower().startswith(rule.match_value.lower())
    if rule.match_type == "regex":
        return _regex_search_with_timeout(rule.match_value, description, timeout)
    return False


def apply_rules(
    rules: list[Rule],
    *,
    description: str,
    amount_cents: int,
    account_id: uuid.UUID,
    timeout: float,
) -> Rule | None:
    """First match wins. `rules` is expected pre-ordered by priority
    (list_rules() below orders by it); enabled=False rules are skipped
    defensively here too, in case a caller passes an unfiltered list.
    """
    for rule in rules:
        if not rule.enabled:
            continue
        if evaluate_rule(
            rule,
            description=description,
            amount_cents=amount_cents,
            account_id=account_id,
            timeout=timeout,
        ):
            return rule
    return None


async def _validate_references(
    db: AsyncSession,
    *,
    household_id: uuid.UUID,
    account_id: uuid.UUID | None,
    set_category_id: uuid.UUID,
) -> None:
    if account_id is not None:
        account = await get_account(db, household_id=household_id, account_id=account_id)
        if account is None:
            raise InvalidReferenceError("Account not found")
    category = await get_category(db, household_id=household_id, category_id=set_category_id)
    if category is None:
        raise InvalidReferenceError("Category not found")


async def _next_priority(db: AsyncSession, household_id: uuid.UUID) -> int:
    stmt = select(func.max(Rule.priority)).where(Rule.household_id == household_id)
    result = await db.execute(stmt)
    current_max = result.scalar_one_or_none()
    return 0 if current_max is None else current_max + 1


async def create_rule(db: AsyncSession, *, household_id: uuid.UUID, payload: RuleCreate) -> Rule:
    _validate_match_pattern(payload.match_type, payload.match_value)
    await _validate_references(
        db,
        household_id=household_id,
        account_id=payload.account_id,
        set_category_id=payload.set_category_id,
    )

    priority = payload.priority
    if priority is None:
        priority = await _next_priority(db, household_id)

    data = payload.model_dump(exclude={"priority"})
    rule = Rule(household_id=household_id, priority=priority, **data)
    db.add(rule)
    await db.flush()
    return rule


async def list_rules(db: AsyncSession, *, household_id: uuid.UUID) -> list[Rule]:
    stmt = select(Rule).where(Rule.household_id == household_id).order_by(Rule.priority)
    result = await db.execute(stmt)
    return list(result.scalars().all())


async def get_rule(
    db: AsyncSession, *, household_id: uuid.UUID, rule_id: uuid.UUID
) -> Rule | None:
    stmt = select(Rule).where(Rule.household_id == household_id, Rule.id == rule_id)
    result = await db.execute(stmt)
    return result.scalar_one_or_none()


async def update_rule(
    db: AsyncSession, *, household_id: uuid.UUID, rule_id: uuid.UUID, payload: RuleUpdate
) -> Rule | None:
    rule = await get_rule(db, household_id=household_id, rule_id=rule_id)
    if rule is None:
        return None

    update_data = payload.model_dump(exclude_unset=True)

    if "match_type" in update_data or "match_value" in update_data:
        _validate_match_pattern(
            update_data.get("match_type", rule.match_type),
            update_data.get("match_value", rule.match_value),
        )

    if "account_id" in update_data or "set_category_id" in update_data:
        await _validate_references(
            db,
            household_id=household_id,
            account_id=update_data.get("account_id", rule.account_id),
            set_category_id=update_data.get("set_category_id", rule.set_category_id),
        )

    for key, value in update_data.items():
        setattr(rule, key, value)
    await db.flush()
    return rule


async def delete_rule(db: AsyncSession, *, household_id: uuid.UUID, rule_id: uuid.UUID) -> bool:
    rule = await get_rule(db, household_id=household_id, rule_id=rule_id)
    if rule is None:
        return False
    await db.delete(rule)
    await db.flush()
    return True


async def reorder_rules(
    db: AsyncSession, *, household_id: uuid.UUID, ordered_ids: list[uuid.UUID]
) -> list[Rule]:
    existing = await list_rules(db, household_id=household_id)
    existing_ids = {r.id for r in existing}
    if len(ordered_ids) != len(existing) or set(ordered_ids) != existing_ids:
        raise RuleError("ordered_ids must contain exactly this household's existing rule ids")

    by_id = {r.id: r for r in existing}
    for index, rule_id in enumerate(ordered_ids):
        by_id[rule_id].priority = index
    await db.flush()
    return await list_rules(db, household_id=household_id)
