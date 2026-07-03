from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_db

router = APIRouter(tags=["health"])


@router.get("/health")
async def liveness() -> dict[str, str]:
    """No dependencies — proves the process is up. Used by Docker/Caddy healthchecks."""
    return {"status": "ok"}


@router.get("/health/ready")
async def readiness(db: Annotated[AsyncSession, Depends(get_db)]) -> dict[str, str]:
    """Proves DB connectivity, not just process liveness."""
    await db.execute(text("SELECT 1"))
    return {"status": "ok"}
