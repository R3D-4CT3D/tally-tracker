"""Built-in merchant-name/description pattern -> category suggestions,
applied through the exact same Rules engine as user-defined rules
(app/services/rules.py's apply_rules/evaluate_rule duck-type over any object
with the right attributes -- a transient, never-persisted Rule instance
works identically to a real one, since apply_rules never calls db.add or
flush). These only fire when nothing in the household's own rules matched
first: app/services/imports.py's _process_rows appends the rules built here
*after* list_rules()'s real results, and apply_rules is first-match-wins
over list order -- so a real user rule always wins over a built-in guess.
"""

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.category import Category
from app.models.rule import Rule

# (match_type, match_value, category_name) -- category_name is looked up
# per-household below, so this list stays storage-agnostic. Interest/fee
# patterns are just as much "merchant pattern matching" as a brand name is,
# from the Rules engine's point of view -- no bank-format-specific code
# needed for Wells Fargo's "Interest Charge" rows beyond an entry here.
_MERCHANT_PATTERNS: tuple[tuple[str, str, str], ...] = (
    ("contains", "arco", "Transport"),
    ("contains", "chevron", "Transport"),
    ("contains", "shell oil", "Transport"),
    ("contains", "exxon", "Transport"),
    ("contains", "uber", "Transport"),
    ("contains", "lyft", "Transport"),
    ("contains", "mcdonald", "Dining"),
    ("contains", "chipotle", "Dining"),
    ("contains", "starbucks", "Dining"),
    ("contains", "doordash", "Dining"),
    ("contains", "amazon", "Misc"),
    ("contains", "24 hour fitness", "Health"),
    ("contains", "planet fitness", "Health"),
    ("contains", "cvs", "Health"),
    ("contains", "walgreens", "Health"),
    ("contains", "netflix", "Subscriptions"),
    ("contains", "spotify", "Subscriptions"),
    ("contains", "interest charge", "Fees"),
    ("contains", "annual fee", "Fees"),
    ("contains", "late fee", "Fees"),
)


async def build_builtin_rules(db: AsyncSession, *, household_id: uuid.UUID) -> list[Rule]:
    """Transient Rule objects (constructed but never added to the session)
    expressing _MERCHANT_PATTERNS, resolved against this household's actual
    categories. A pattern whose target category doesn't exist for this
    household (renamed/deleted) is silently skipped rather than erroring --
    these are best-effort suggestions, not a hard requirement.
    """
    category_ids: dict[str, uuid.UUID] = {}
    rules: list[Rule] = []
    for priority, (match_type, match_value, category_name) in enumerate(_MERCHANT_PATTERNS):
        if category_name not in category_ids:
            stmt = select(Category.id).where(
                Category.household_id == household_id, Category.name == category_name
            )
            result = await db.execute(stmt)
            category_id = result.scalar_one_or_none()
            if category_id is None:
                continue
            category_ids[category_name] = category_id

        rules.append(
            Rule(
                household_id=household_id,
                priority=10_000 + priority,
                match_type=match_type,
                match_value=match_value,
                amount_min=None,
                amount_max=None,
                account_id=None,
                set_category_id=category_ids[category_name],
                set_display_name=None,
                enabled=True,
            )
        )
    return rules
