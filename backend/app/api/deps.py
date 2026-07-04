from typing import Annotated

from fastapi import Depends, Header, HTTPException, Request, status
from redis.asyncio import Redis

from app.core.config import get_settings
from app.core.redis import get_redis
from app.core.security import CSRF_COOKIE_NAME, SESSION_COOKIE_NAME, SessionData, load_session

settings = get_settings()


async def get_current_user(
    request: Request,
    redis: Annotated[Redis, Depends(get_redis)],
) -> SessionData:
    """The household-scoping dependency: every route that touches
    household-scoped data depends on this (directly or via require_role) and
    reads `.household_id` from it — never from a client-supplied param.

    Built entirely from the Redis session payload cached at login time, no DB
    hit per request (see docs/adr and the M1 plan for the tradeoff).
    """
    session_id = request.cookies.get(SESSION_COOKIE_NAME)
    if session_id is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Not authenticated")

    session = await load_session(redis, session_id, idle_days=settings.session_idle_days)
    if session is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Session expired or invalid")
    return session


CurrentUser = Annotated[SessionData, Depends(get_current_user)]


def require_role(*roles: str) -> object:
    async def _check(current_user: CurrentUser) -> SessionData:
        if current_user.role not in roles:
            raise HTTPException(status.HTTP_403_FORBIDDEN, "Insufficient permissions")
        return current_user

    return Depends(_check)


async def stash_household_for_rate_limit(current_user: CurrentUser, request: Request) -> None:
    """slowapi's key_func must be synchronous, so it can't read the (async,
    Redis-backed) session itself -- this dependency resolves CurrentUser
    first and stashes household_id onto request.state for
    app.core.limiter.import_rate_limit_key to read afterward. Same pattern
    as cache_login_email/login_rate_limit_key for the login endpoint.
    """
    request.state.import_household_id = current_user.household_id


async def verify_csrf(
    request: Request,
    current_user: CurrentUser,
    x_csrf_token: Annotated[str | None, Header()] = None,
) -> None:
    cookie_token = request.cookies.get(CSRF_COOKIE_NAME)
    if (
        not x_csrf_token
        or not cookie_token
        or x_csrf_token != cookie_token
        or x_csrf_token != current_user.csrf_token
    ):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "CSRF token missing or invalid")
