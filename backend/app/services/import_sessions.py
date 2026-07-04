import json
import secrets
import uuid
from typing import Literal

from pydantic import BaseModel
from redis.asyncio import Redis


class ImportSessionData(BaseModel):
    session_id: str
    household_id: str
    filename: str | None
    source: Literal["csv", "paste"]
    header: list[str]
    rows: list[list[str]]


def _session_key(session_id: str) -> str:
    return f"import_session:{session_id}"


async def create_import_session(
    redis: Redis,
    *,
    household_id: uuid.UUID,
    filename: str | None,
    source: Literal["csv", "paste"],
    header: list[str],
    rows: list[list[str]],
    ttl_seconds: int,
) -> ImportSessionData:
    """Caches the raw (unparsed) rows only -- date_format/column_mapping are
    supplied fresh on every preview/commit call, so the user can go back and
    fix the mapping without re-uploading the file. Stateless-API-friendly
    per docs/TALLY_BUILD_SPEC.md §6b: this is Redis state, not in-process.
    """
    session = ImportSessionData(
        session_id=secrets.token_urlsafe(24),
        household_id=str(household_id),
        filename=filename,
        source=source,
        header=header,
        rows=rows,
    )
    await redis.set(_session_key(session.session_id), session.model_dump_json(), ex=ttl_seconds)
    return session


async def get_import_session(
    redis: Redis, *, session_id: str, household_id: uuid.UUID
) -> ImportSessionData | None:
    """Returns None both when the session doesn't exist and when it belongs
    to a different household -- same 404-not-403 discipline as every other
    household-scoped lookup in this codebase (a 403 would confirm the
    session id exists somewhere, just not for the caller).
    """
    raw = await redis.get(_session_key(session_id))
    if raw is None:
        return None
    session = ImportSessionData.model_validate(json.loads(raw))
    if session.household_id != str(household_id):
        return None
    return session


async def delete_import_session(redis: Redis, session_id: str) -> None:
    await redis.delete(_session_key(session_id))
