from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.audit_log import AuditLog
from tests.conftest import SETUP_PAYLOAD


async def _logout(client: AsyncClient) -> None:
    csrf_token = client.cookies.get("tally_csrf")
    assert csrf_token is not None
    await client.post("/api/v1/auth/logout", headers={"X-CSRF-Token": csrf_token})


async def test_login_success_sets_cookies_and_records_audit_event(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    await client.post("/api/v1/setup", json=SETUP_PAYLOAD)
    await _logout(client)

    resp = await client.post(
        "/api/v1/auth/login",
        json={
            "email": SETUP_PAYLOAD["owner_email"],
            "password": SETUP_PAYLOAD["owner_password"],
        },
    )
    assert resp.status_code == 200
    assert "tally_session" in resp.cookies
    assert "tally_csrf" in resp.cookies

    result = await db_session.execute(select(AuditLog).where(AuditLog.action == "login_success"))
    assert result.scalar_one_or_none() is not None


async def test_login_failure_is_generic_regardless_of_which_field_is_wrong(
    client: AsyncClient,
) -> None:
    await client.post("/api/v1/setup", json=SETUP_PAYLOAD)

    wrong_password = await client.post(
        "/api/v1/auth/login",
        json={"email": SETUP_PAYLOAD["owner_email"], "password": "wrong-password-xyz"},
    )
    unknown_email = await client.post(
        "/api/v1/auth/login",
        json={"email": "nobody-here@example.com", "password": "wrong-password-xyz"},
    )
    assert wrong_password.status_code == 401
    assert unknown_email.status_code == 401
    assert wrong_password.json() == unknown_email.json()


async def test_logout_requires_csrf_then_clears_session(client: AsyncClient) -> None:
    await client.post("/api/v1/setup", json=SETUP_PAYLOAD)

    no_csrf = await client.post("/api/v1/auth/logout")
    assert no_csrf.status_code == 403

    still_authenticated = await client.get("/api/v1/auth/me")
    assert still_authenticated.status_code == 200

    csrf_token = client.cookies.get("tally_csrf")
    assert csrf_token is not None
    with_csrf = await client.post("/api/v1/auth/logout", headers={"X-CSRF-Token": csrf_token})
    assert with_csrf.status_code == 200

    after_logout = await client.get("/api/v1/auth/me")
    assert after_logout.status_code == 401


async def test_login_rate_limit_is_keyed_by_ip_and_account(client: AsyncClient) -> None:
    await client.post("/api/v1/setup", json=SETUP_PAYLOAD)
    await _logout(client)

    for _ in range(5):
        resp = await client.post(
            "/api/v1/auth/login",
            json={"email": SETUP_PAYLOAD["owner_email"], "password": "wrong-password"},
        )
        assert resp.status_code == 401

    sixth = await client.post(
        "/api/v1/auth/login",
        json={"email": SETUP_PAYLOAD["owner_email"], "password": "wrong-password"},
    )
    assert sixth.status_code == 429

    # Even the *correct* password is blocked now for this account+IP.
    still_blocked = await client.post(
        "/api/v1/auth/login",
        json={
            "email": SETUP_PAYLOAD["owner_email"],
            "password": SETUP_PAYLOAD["owner_password"],
        },
    )
    assert still_blocked.status_code == 429

    # A different account from the same client (same IP) is unaffected —
    # proves the key is IP+account, not IP alone.
    unaffected = await client.post(
        "/api/v1/auth/login",
        json={"email": "totally-different@example.com", "password": "irrelevant"},
    )
    assert unaffected.status_code == 401
