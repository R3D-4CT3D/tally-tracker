import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.category import Category
from app.schemas.categories import CategoryCreate, CategoryUpdate

# The 13 categories from docs/TALLY_BUILD_SPEC.md §4.2, seeded once per
# household at setup time (see app/services/household.py). Colors are
# placeholder-but-real -- swapped for the M5 design system's real palette,
# not re-derived from scratch.
DEFAULT_CATEGORIES: list[dict[str, str]] = [
    {"name": "Housing", "icon": "🏠", "color": "#B45309"},
    {"name": "Utilities", "icon": "💡", "color": "#0EA5E9"},
    {"name": "Groceries", "icon": "🛒", "color": "#16A34A"},
    {"name": "Dining", "icon": "🍽️", "color": "#F97316"},
    {"name": "Transport", "icon": "🚗", "color": "#6366F1"},
    {"name": "Insurance", "icon": "🛡️", "color": "#64748B"},
    {"name": "Subscriptions", "icon": "🔁", "color": "#8B5CF6"},
    {"name": "Health", "icon": "➕", "color": "#EF4444"},
    {"name": "Entertainment", "icon": "🎬", "color": "#EC4899"},
    {"name": "Debt Payment", "icon": "💳", "color": "#DC2626"},
    {"name": "Savings", "icon": "🐷", "color": "#059669"},
    {"name": "Income", "icon": "💰", "color": "#CA8A04"},
    {"name": "Misc", "icon": "📦", "color": "#71717A"},
]


class CategoryError(Exception):
    """Invalid parent (missing, or already a subcategory itself -- one level
    of subcategories max)."""


async def seed_default_categories(db: AsyncSession, household_id: uuid.UUID) -> None:
    for entry in DEFAULT_CATEGORIES:
        db.add(Category(household_id=household_id, is_system=True, **entry))
    await db.flush()


async def get_category(
    db: AsyncSession, *, household_id: uuid.UUID, category_id: uuid.UUID
) -> Category | None:
    stmt = select(Category).where(
        Category.household_id == household_id, Category.id == category_id
    )
    result = await db.execute(stmt)
    return result.scalar_one_or_none()


async def _validate_parent(
    db: AsyncSession, *, household_id: uuid.UUID, parent_id: uuid.UUID, self_id: uuid.UUID | None
) -> None:
    if self_id is not None and parent_id == self_id:
        raise CategoryError("A category cannot be its own parent")
    parent = await get_category(db, household_id=household_id, category_id=parent_id)
    if parent is None:
        raise CategoryError("Parent category not found")
    if parent.parent_id is not None:
        raise CategoryError("Subcategories can only be one level deep")
    if self_id is not None:
        # Re-parenting an existing category: if it already has children of
        # its own, giving it a parent would make those children
        # grandchildren of `parent` -- a second level of depth reached
        # indirectly rather than by the direct parent_id being validated
        # above.
        stmt = select(Category.id).where(Category.parent_id == self_id).limit(1)
        result = await db.execute(stmt)
        if result.scalar_one_or_none() is not None:
            raise CategoryError("A category with subcategories cannot itself become a subcategory")


async def create_category(
    db: AsyncSession, *, household_id: uuid.UUID, payload: CategoryCreate
) -> Category:
    if payload.parent_id is not None:
        await _validate_parent(
            db, household_id=household_id, parent_id=payload.parent_id, self_id=None
        )
    category = Category(household_id=household_id, **payload.model_dump())
    db.add(category)
    await db.flush()
    return category


async def list_categories(db: AsyncSession, *, household_id: uuid.UUID) -> list[Category]:
    stmt = (
        select(Category).where(Category.household_id == household_id).order_by(Category.name)
    )
    result = await db.execute(stmt)
    return list(result.scalars().all())


async def update_category(
    db: AsyncSession, *, household_id: uuid.UUID, category_id: uuid.UUID, payload: CategoryUpdate
) -> Category | None:
    category = await get_category(db, household_id=household_id, category_id=category_id)
    if category is None:
        return None

    update_data = payload.model_dump(exclude_unset=True)
    new_parent_id = update_data.get("parent_id")
    if "parent_id" in update_data and new_parent_id is not None:
        await _validate_parent(
            db, household_id=household_id, parent_id=new_parent_id, self_id=category.id
        )

    for key, value in update_data.items():
        setattr(category, key, value)
    await db.flush()
    return category
