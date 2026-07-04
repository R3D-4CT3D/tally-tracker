import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import CurrentUser, verify_csrf
from app.core.db import get_db
from app.schemas.categories import CategoryCreate, CategoryOut, CategoryUpdate
from app.services.categories import CategoryError, create_category, list_categories, update_category

router = APIRouter(prefix="/categories", tags=["categories"])


@router.post(
    "",
    response_model=CategoryOut,
    dependencies=[Depends(verify_csrf)],
    status_code=status.HTTP_201_CREATED,
)
async def create_category_route(
    payload: CategoryCreate,
    current_user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> CategoryOut:
    try:
        category = await create_category(
            db, household_id=uuid.UUID(current_user.household_id), payload=payload
        )
    except CategoryError as exc:
        await db.rollback()
        raise HTTPException(status.HTTP_400_BAD_REQUEST, str(exc)) from exc
    await db.commit()
    return CategoryOut.model_validate(category)


@router.get("", response_model=list[CategoryOut])
async def list_categories_route(
    current_user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> list[CategoryOut]:
    categories = await list_categories(db, household_id=uuid.UUID(current_user.household_id))
    return [CategoryOut.model_validate(c) for c in categories]


@router.patch("/{category_id}", response_model=CategoryOut, dependencies=[Depends(verify_csrf)])
async def update_category_route(
    category_id: uuid.UUID,
    payload: CategoryUpdate,
    current_user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> CategoryOut:
    try:
        category = await update_category(
            db,
            household_id=uuid.UUID(current_user.household_id),
            category_id=category_id,
            payload=payload,
        )
    except CategoryError as exc:
        await db.rollback()
        raise HTTPException(status.HTTP_400_BAD_REQUEST, str(exc)) from exc
    if category is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Category not found")
    await db.commit()
    return CategoryOut.model_validate(category)
