import json
import secrets
from datetime import UTC, datetime, timedelta

from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError
from fastapi import Response
from pydantic import BaseModel
from redis.asyncio import Redis

SESSION_COOKIE_NAME = "tally_session"
CSRF_COOKIE_NAME = "tally_csrf"

_hasher = PasswordHasher()

# Precomputed once so verifying against a nonexistent user takes about as long
# as verifying against a real one — avoids leaking "this email doesn't exist"
# via response timing.
_DUMMY_HASH = _hasher.hash("dummy-password-for-constant-time-comparison")


def hash_password(password: str) -> str:
    return _hasher.hash(password)


def verify_password(password: str, password_hash: str | None) -> bool:
    """Verify a password against a hash. If password_hash is None (user not
    found), still runs a full Argon2 verify against a dummy hash so callers
    can't distinguish "wrong password" from "no such user" by timing.
    """
    target = password_hash if password_hash is not None else _DUMMY_HASH
    try:
        _hasher.verify(target, password)
    except VerifyMismatchError:
        return False
    return password_hash is not None


class SessionData(BaseModel):
    session_id: str
    user_id: str
    household_id: str
    household_name: str
    role: str
    email: str
    display_name: str
    csrf_token: str
    created_at: datetime
    absolute_expires_at: datetime
    # The user's *previous* last_login_at, captured once at login and baked
    # into the session for its whole lifetime (M5) -- "since you were here"
    # should mean since this session started, not a value that moves mid-session.
    last_login_at: datetime | None = None


def _session_key(session_id: str) -> str:
    return f"session:{session_id}"


def _user_sessions_key(user_id: str) -> str:
    return f"user_sessions:{user_id}"


async def create_session(
    redis: Redis,
    *,
    user_id: str,
    household_id: str,
    household_name: str,
    role: str,
    email: str,
    display_name: str,
    idle_days: int,
    absolute_days: int,
    last_login_at: datetime | None = None,
) -> SessionData:
    """Always mints a brand-new session id — never reuses/extends an existing
    one — so a fresh login always rotates the session (mitigates fixation).
    """
    now = datetime.now(UTC)
    session = SessionData(
        session_id=secrets.token_urlsafe(32),
        user_id=user_id,
        household_id=household_id,
        household_name=household_name,
        role=role,
        email=email,
        display_name=display_name,
        csrf_token=secrets.token_urlsafe(32),
        created_at=now,
        absolute_expires_at=now + timedelta(days=absolute_days),
        last_login_at=last_login_at,
    )
    idle_seconds = idle_days * 86400
    async with redis.pipeline(transaction=True) as pipe:
        pipe.set(_session_key(session.session_id), session.model_dump_json(), ex=idle_seconds)
        pipe.sadd(_user_sessions_key(user_id), session.session_id)
        await pipe.execute()
    return session


async def load_session(redis: Redis, session_id: str, *, idle_days: int) -> SessionData | None:
    """Loads a session, enforcing the absolute expiry explicitly (Redis TTL
    alone only implements the sliding idle timeout, not a hard cap), and
    refreshes the idle TTL on successful load — capped so it never extends
    past absolute_expires_at.
    """
    raw = await redis.get(_session_key(session_id))
    if raw is None:
        return None
    session = SessionData.model_validate(json.loads(raw))

    now = datetime.now(UTC)
    if now >= session.absolute_expires_at:
        await delete_session(redis, session_id, session.user_id)
        return None

    idle_seconds = idle_days * 86400
    remaining_absolute = int((session.absolute_expires_at - now).total_seconds())
    ttl = min(idle_seconds, remaining_absolute)
    if ttl > 0:
        await redis.expire(_session_key(session_id), ttl)
    return session


async def delete_session(redis: Redis, session_id: str, user_id: str) -> None:
    async with redis.pipeline(transaction=True) as pipe:
        pipe.delete(_session_key(session_id))
        pipe.srem(_user_sessions_key(user_id), session_id)
        await pipe.execute()


def set_session_cookies(response: Response, session: SessionData) -> None:
    response.set_cookie(
        SESSION_COOKIE_NAME,
        session.session_id,
        httponly=True,
        secure=True,
        samesite="lax",
        path="/",
    )
    response.set_cookie(
        CSRF_COOKIE_NAME,
        session.csrf_token,
        httponly=False,
        secure=True,
        samesite="lax",
        path="/",
    )


def clear_session_cookies(response: Response) -> None:
    response.delete_cookie(SESSION_COOKIE_NAME, path="/")
    response.delete_cookie(CSRF_COOKIE_NAME, path="/")


def generate_invite_token() -> str:
    return secrets.token_urlsafe(32)


def hash_invite_token(token: str) -> str:
    import hashlib

    return hashlib.sha256(token.encode()).hexdigest()
