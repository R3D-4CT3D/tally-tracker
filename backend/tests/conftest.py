import os

# Must happen before any app module is imported: app.core.limiter builds its
# module-level Limiter singleton from settings.rate_limit_storage_uri at
# import time. Tests use in-process memory storage instead of real Redis so
# CI doesn't need a second service container just for rate-limit counters.
os.environ.setdefault("RATE_LIMIT_STORAGE_URI", "memory://")

from collections.abc import AsyncGenerator  # noqa: E402

import pytest  # noqa: E402
from alembic.config import Config  # noqa: E402
from fakeredis import aioredis as fake_aioredis  # noqa: E402
from httpx import ASGITransport, AsyncClient  # noqa: E402
from redis.asyncio import Redis  # noqa: E402
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, create_async_engine  # noqa: E402

from alembic import command  # noqa: E402
from app.core.config import get_settings  # noqa: E402
from app.core.db import get_db  # noqa: E402
from app.core.limiter import limiter  # noqa: E402
from app.core.redis import get_redis  # noqa: E402
from app.core.security import SessionData, create_session  # noqa: E402
from app.main import app  # noqa: E402
from app.models.household import Household  # noqa: E402
from app.models.household_member import HouseholdMember  # noqa: E402
from app.models.user import User  # noqa: E402
from app.services.household import create_household_and_owner  # noqa: E402

settings = get_settings()


@pytest.fixture(autouse=True)
def reset_rate_limiter() -> None:
    """The Limiter is a module-level singleton with in-memory (memory://)
    storage in tests — without this, failed-login counts from one test would
    bleed into the next.
    """
    limiter.reset()


@pytest.fixture(scope="session", autouse=True)
def apply_migrations() -> None:
    """Runs alembic upgrade head against settings.database_url once per test
    session — real Postgres, real migrations, not a metadata.create_all()
    shortcut (see the M1 plan's verification section for why).
    """
    command.upgrade(Config("alembic.ini"), "head")


@pytest.fixture()
async def test_engine() -> AsyncGenerator[AsyncEngine, None]:
    engine = create_async_engine(settings.database_url)
    yield engine
    await engine.dispose()


@pytest.fixture()
async def db_session(test_engine: AsyncEngine) -> AsyncGenerator[AsyncSession, None]:
    """Wraps each test in an outer transaction + SAVEPOINT (join_transaction_mode
    create_savepoint) and rolls it back at teardown, so app code's own
    `await db.commit()` calls just release/recreate savepoints instead of
    persisting anything — full isolation between tests without truncating
    tables.
    """
    async with test_engine.connect() as connection:
        await connection.begin()
        session = AsyncSession(
            bind=connection, join_transaction_mode="create_savepoint", expire_on_commit=False
        )
        try:
            yield session
        finally:
            await session.close()
            await connection.rollback()


@pytest.fixture()
async def fake_redis() -> AsyncGenerator[Redis, None]:
    client = fake_aioredis.FakeRedis(decode_responses=True)
    yield client
    await client.aclose()


@pytest.fixture()
async def client(
    db_session: AsyncSession, fake_redis: Redis
) -> AsyncGenerator[AsyncClient, None]:
    async def _get_db() -> AsyncGenerator[AsyncSession, None]:
        yield db_session

    async def _get_redis() -> AsyncGenerator[Redis, None]:
        yield fake_redis

    app.dependency_overrides[get_db] = _get_db
    app.dependency_overrides[get_redis] = _get_redis
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="https://test") as ac:
        yield ac
    app.dependency_overrides.clear()


async def seed_household(
    db_session: AsyncSession,
    fake_redis: Redis,
    *,
    household_name: str,
    owner_email: str,
    owner_display_name: str = "Owner",
    owner_password: str = "correcthorsebattery123",
) -> tuple[Household, User, HouseholdMember, SessionData]:
    """Creates a household + owner directly via the service layer, bypassing
    HTTP. This is the *only* way to get a second household in tests, since
    /setup intentionally only succeeds once per instance — see the M1 plan's
    architectural note on cross-household isolation testing.
    """
    household, user, member = await create_household_and_owner(
        db_session,
        household_name=household_name,
        owner_email=owner_email,
        owner_display_name=owner_display_name,
        owner_password=owner_password,
    )
    await db_session.commit()
    session = await create_session(
        fake_redis,
        user_id=str(user.id),
        household_id=str(household.id),
        household_name=household.name,
        role=member.role,
        email=user.email,
        display_name=user.display_name,
        idle_days=settings.session_idle_days,
        absolute_days=settings.session_absolute_days,
    )
    return household, user, member, session


def apply_session_cookies(client: AsyncClient, session: SessionData) -> None:
    """Clears first: a prior request that itself set cookies via a real
    Set-Cookie response (e.g. invite-accept auto-login) leaves an entry in
    httpx's jar that a same-name .set() call doesn't reliably fully replace
    (they can end up tracked under different internal domains) — clearing
    avoids that ambiguity entirely rather than fighting cookie-jar semantics.
    """
    client.cookies.clear()
    client.cookies.set("tally_session", session.session_id)
    client.cookies.set("tally_csrf", session.csrf_token)


SETUP_PAYLOAD = {
    "household_name": "The Test Household",
    "owner_email": "owner@example.com",
    "owner_display_name": "Owner",
    "owner_password": "correcthorsebattery123",
}


async def do_setup(client: AsyncClient, **overrides: str) -> AsyncClient:
    await client.post("/api/v1/setup", json={**SETUP_PAYLOAD, **overrides})
    return client
