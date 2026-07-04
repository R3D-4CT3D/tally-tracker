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


async def test_core_entities_are_household_scoped(
    client: AsyncClient, db_session: AsyncSession, fake_redis: Redis
) -> None:
    """Accounts, categories, and transactions created under household A must
    be invisible to household B — both via the list endpoints and via direct
    get-by-id, which is the case a client-supplied household_id bug would
    actually leak through (list filters hide it; a stray id doesn't).
    """
    _, _, _, session_a = await seed_household(
        db_session, fake_redis, household_name="Household A", owner_email="ownera2@example.com"
    )
    _, _, _, session_b = await seed_household(
        db_session, fake_redis, household_name="Household B", owner_email="ownerb2@example.com"
    )

    apply_session_cookies(client, session_a)
    account_resp = await client.post(
        "/api/v1/accounts",
        json={
            "name": "A's Checking",
            "type": "checking",
            "balance_cents": 0,
            "color": "#336699",
            "icon": "bank",
        },
        headers={"X-CSRF-Token": session_a.csrf_token},
    )
    assert account_resp.status_code == 201
    account_a = account_resp.json()

    category_resp = await client.post(
        "/api/v1/categories",
        json={"name": "A's Category", "icon": "star", "color": "#ABCDEF"},
        headers={"X-CSRF-Token": session_a.csrf_token},
    )
    assert category_resp.status_code == 201
    category_a = category_resp.json()

    transaction_resp = await client.post(
        "/api/v1/transactions",
        json={
            "account_id": account_a["id"],
            "date": "2026-01-15",
            "amount_cents": -1000,
            "description": "A's transaction",
            "category_id": category_a["id"],
        },
        headers={"X-CSRF-Token": session_a.csrf_token},
    )
    assert transaction_resp.status_code == 201
    transaction_a = transaction_resp.json()

    apply_session_cookies(client, session_b)

    assert (await client.get("/api/v1/accounts")).json() == []
    assert (await client.get(f"/api/v1/accounts/{account_a['id']}")).status_code == 404

    category_names_b = {c["name"] for c in (await client.get("/api/v1/categories")).json()}
    assert "A's Category" not in category_names_b

    assert (await client.get("/api/v1/transactions")).json()["items"] == []
    assert (
        await client.get(f"/api/v1/transactions/{transaction_a['id']}")
    ).status_code == 404

    # A client-supplied household_id must not override the session's -- there
    # is no such field in the request bodies at all, but prove B genuinely
    # cannot mutate A's rows even by guessing A's entity ids.
    patch_resp = await client.patch(
        f"/api/v1/accounts/{account_a['id']}",
        json={"name": "Hijacked"},
        headers={"X-CSRF-Token": session_b.csrf_token},
    )
    assert patch_resp.status_code == 404
