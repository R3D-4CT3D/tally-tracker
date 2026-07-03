from httpx import AsyncClient
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from tests.conftest import apply_session_cookies, seed_household


async def test_cross_household_isolation(
    client: AsyncClient, db_session: AsyncSession, fake_redis: Redis
) -> None:
    """Seeds two households directly via the service layer — this is the only
    way to get a second household in tests, since /setup intentionally only
    succeeds once per instance (see docs/adr and the M1 plan's architectural
    note). Proves the household-scoping dependency, not just the setup UX.
    """
    _, _, _, session_a = await seed_household(
        db_session, fake_redis, household_name="Household A", owner_email="ownera@example.com"
    )
    _, _, _, session_b = await seed_household(
        db_session, fake_redis, household_name="Household B", owner_email="ownerb@example.com"
    )

    apply_session_cookies(client, session_a)
    invite_a = await client.post(
        "/api/v1/invites", headers={"X-CSRF-Token": session_a.csrf_token}
    )
    assert invite_a.status_code == 200

    apply_session_cookies(client, session_b)
    invite_b = await client.post(
        "/api/v1/invites", headers={"X-CSRF-Token": session_b.csrf_token}
    )
    assert invite_b.status_code == 200

    # As A: only A's invite and A's single member are visible — never B's.
    apply_session_cookies(client, session_a)
    invites_as_a = await client.get("/api/v1/invites")
    assert invites_as_a.status_code == 200
    assert len(invites_as_a.json()) == 1

    members_as_a = await client.get("/api/v1/household/members")
    assert len(members_as_a.json()) == 1
    assert members_as_a.json()[0]["email"] == "ownera@example.com"

    # Symmetric check as B.
    apply_session_cookies(client, session_b)
    invites_as_b = await client.get("/api/v1/invites")
    assert len(invites_as_b.json()) == 1
    members_as_b = await client.get("/api/v1/household/members")
    assert len(members_as_b.json()) == 1
    assert members_as_b.json()[0]["email"] == "ownerb@example.com"

    # Accepting B's invite while authenticated as A: accept is identity-based
    # via the token (not session-scoped) — a user isn't expected to have an
    # existing session in V1's one-household-per-user model, but this proves
    # it doesn't leak or corrupt A's membership either way.
    apply_session_cookies(client, session_a)
    accept_resp = await client.post(
        "/api/v1/invites/accept",
        json={
            "token": invite_b.json()["token"],
            "email": "joins-b@example.com",
            "display_name": "Joins B",
            "password": "correcthorsebattery000",
        },
    )
    assert accept_resp.status_code == 200

    apply_session_cookies(client, session_b)
    members_as_b_after = await client.get("/api/v1/household/members")
    emails_b = {m["email"] for m in members_as_b_after.json()}
    assert emails_b == {"ownerb@example.com", "joins-b@example.com"}

    apply_session_cookies(client, session_a)
    members_as_a_after = await client.get("/api/v1/household/members")
    assert len(members_as_a_after.json()) == 1
    assert members_as_a_after.json()[0]["email"] == "ownera@example.com"
