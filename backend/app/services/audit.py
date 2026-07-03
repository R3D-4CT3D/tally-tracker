import uuid
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.audit_log import AuditLog


async def record_audit_event(
    db: AsyncSession,
    *,
    household_id: uuid.UUID | None,
    user_id: uuid.UUID | None,
    action: str,
    entity: str,
    entity_id: uuid.UUID | None = None,
    meta: dict[str, Any] | None = None,
    ip: str | None = None,
) -> None:
    db.add(
        AuditLog(
            household_id=household_id,
            user_id=user_id,
            action=action,
            entity=entity,
            entity_id=entity_id,
            meta=meta or {},
            ip=ip,
        )
    )
    await db.flush()
