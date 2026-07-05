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


async def test_import_batches_and_profiles_are_household_scoped(
    client: AsyncClient, db_session: AsyncSession, fake_redis: Redis
) -> None:
    _, _, _, session_a = await seed_household(
        db_session, fake_redis, household_name="Household A", owner_email="ownera4@example.com"
    )
    _, _, _, session_b = await seed_household(
        db_session, fake_redis, household_name="Household B", owner_email="ownerb4@example.com"
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
    account_id = account_resp.json()["id"]

    profile_resp = await client.post(
        "/api/v1/import-profiles",
        json={
            "name": "A's Profile",
            "column_mapping": {"date": "Date", "description": "Description", "amount": "Amount"},
            "date_format": "MDY",
        },
        headers={"X-CSRF-Token": session_a.csrf_token},
    )
    profile_a = profile_resp.json()

    upload_resp = await client.post(
        "/api/v1/imports/paste",
        json={"text": "Date,Description,Amount\n01/15/2026,Coffee,-4.50\n"},
        headers={"X-CSRF-Token": session_a.csrf_token},
    )
    session_id = upload_resp.json()["import_session_id"]
    commit_resp = await client.post(
        f"/api/v1/imports/{session_id}/commit",
        json={
            "column_mapping": {"date": "Date", "description": "Description", "amount": "Amount"},
            "date_format": "MDY",
            "account_id": account_id,
        },
        headers={"X-CSRF-Token": session_a.csrf_token},
    )
    batch_a = commit_resp.json()

    apply_session_cookies(client, session_b)

    profiles_b = await client.get("/api/v1/import-profiles")
    assert profiles_b.json() == []
    delete_profile_resp = await client.delete(
        f"/api/v1/import-profiles/{profile_a['id']}",
        headers={"X-CSRF-Token": session_b.csrf_token},
    )
    assert delete_profile_resp.status_code == 404

    batches_b = await client.get("/api/v1/imports/batches")
    assert batches_b.json() == []
    undo_resp = await client.delete(
        f"/api/v1/imports/batches/{batch_a['id']}",
        headers={"X-CSRF-Token": session_b.csrf_token},
    )
    assert undo_resp.status_code == 404

    # B cannot reuse A's import session id (upload cache) either.
    preview_resp = await client.post(
        f"/api/v1/imports/{session_id}/preview",
        json={
            "column_mapping": {"date": "Date", "description": "Description", "amount": "Amount"},
            "date_format": "MDY",
            "account_id": account_id,
        },
    )
    assert preview_resp.status_code == 404

    apply_session_cookies(client, session_a)
    batches_a_after = await client.get("/api/v1/imports/batches")
    assert len(batches_a_after.json()) == 1


async def test_transaction_cannot_reference_another_households_account_or_category(
    client: AsyncClient, db_session: AsyncSession, fake_redis: Redis
) -> None:
    """A transaction's account_id/category_id are client-supplied FK
    references, not just filters -- unlike a stray get-by-id (which a
    household-scoped WHERE clause naturally hides), storing an unvalidated
    cross-household id as a foreign key would succeed unless the referenced
    row is itself confirmed to belong to the caller's household first.
    """
    _, _, _, session_a = await seed_household(
        db_session, fake_redis, household_name="Household A", owner_email="ownera3@example.com"
    )
    _, _, _, session_b = await seed_household(
        db_session, fake_redis, household_name="Household B", owner_email="ownerb3@example.com"
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
    account_a_id = account_resp.json()["id"]
    category_a_id = (await client.get("/api/v1/categories")).json()[0]["id"]

    apply_session_cookies(client, session_b)
    account_b_resp = await client.post(
        "/api/v1/accounts",
        json={
            "name": "B's Checking",
            "type": "checking",
            "balance_cents": 0,
            "color": "#336699",
            "icon": "bank",
        },
        headers={"X-CSRF-Token": session_b.csrf_token},
    )
    account_b_id = account_b_resp.json()["id"]

    # B tries to create a transaction against A's account -- must be rejected,
    # not silently stored with a foreign key into another household's data.
    create_resp = await client.post(
        "/api/v1/transactions",
        json={
            "account_id": account_a_id,
            "date": "2026-01-15",
            "amount_cents": -500,
            "description": "Cross-household attempt",
        },
        headers={"X-CSRF-Token": session_b.csrf_token},
    )
    assert create_resp.status_code == 404

    # B tries to create a transaction against B's own account but A's category.
    create_resp_category = await client.post(
        "/api/v1/transactions",
        json={
            "account_id": account_b_id,
            "date": "2026-01-15",
            "amount_cents": -500,
            "description": "Cross-household category attempt",
            "category_id": category_a_id,
        },
        headers={"X-CSRF-Token": session_b.csrf_token},
    )
    assert create_resp_category.status_code == 404

    # A legitimate transaction for B, then try to re-point it at A's account
    # via update.
    valid_resp = await client.post(
        "/api/v1/transactions",
        json={
            "account_id": account_b_id,
            "date": "2026-01-15",
            "amount_cents": -500,
            "description": "B's real transaction",
        },
        headers={"X-CSRF-Token": session_b.csrf_token},
    )
    assert valid_resp.status_code == 201
    transaction_b_id = valid_resp.json()["id"]

    update_resp = await client.patch(
        f"/api/v1/transactions/{transaction_b_id}",
        json={"account_id": account_a_id},
        headers={"X-CSRF-Token": session_b.csrf_token},
    )
    assert update_resp.status_code == 404


async def test_debts_bills_goals_are_household_scoped(
    client: AsyncClient, db_session: AsyncSession, fake_redis: Redis
) -> None:
    """M4 entities must follow the same isolation shape as M2/M3: hidden from
    list, 404 on direct get-by-id, and 404 when B tries to mutate A's rows
    even by guessing A's entity ids.
    """
    _, _, _, session_a = await seed_household(
        db_session, fake_redis, household_name="Household A", owner_email="ownera5@example.com"
    )
    _, _, _, session_b = await seed_household(
        db_session, fake_redis, household_name="Household B", owner_email="ownerb5@example.com"
    )

    apply_session_cookies(client, session_a)
    debt_resp = await client.post(
        "/api/v1/debts",
        json={
            "name": "A's Card",
            "type": "credit_card",
            "original_balance_cents": 10000,
            "current_balance_cents": 10000,
            "apr_bps": 1999,
            "min_payment_cents": 2500,
            "due_day": 15,
        },
        headers={"X-CSRF-Token": session_a.csrf_token},
    )
    debt_a = debt_resp.json()

    bill_resp = await client.post(
        "/api/v1/bills",
        json={
            "name": "A's Bill",
            "amount_cents": 5000,
            "frequency": "monthly",
            "due_day": 1,
            "next_due_date": "2026-01-01",
        },
        headers={"X-CSRF-Token": session_a.csrf_token},
    )
    bill_a = bill_resp.json()

    goal_resp = await client.post(
        "/api/v1/goals",
        json={"name": "A's Goal", "target_cents": 100000, "icon": "🐷", "color": "#059669"},
        headers={"X-CSRF-Token": session_a.csrf_token},
    )
    goal_a = goal_resp.json()

    apply_session_cookies(client, session_b)

    assert (await client.get("/api/v1/debts")).json() == []
    assert (await client.get(f"/api/v1/debts/{debt_a['id']}")).status_code == 404
    assert (
        await client.patch(
            f"/api/v1/debts/{debt_a['id']}",
            json={"name": "Hijacked"},
            headers={"X-CSRF-Token": session_b.csrf_token},
        )
    ).status_code == 404

    assert (await client.get("/api/v1/bills")).json() == []
    assert (await client.get(f"/api/v1/bills/{bill_a['id']}")).status_code == 404
    assert (
        await client.patch(
            f"/api/v1/bills/{bill_a['id']}",
            json={"name": "Hijacked"},
            headers={"X-CSRF-Token": session_b.csrf_token},
        )
    ).status_code == 404

    assert (await client.get("/api/v1/goals")).json() == []
    assert (await client.get(f"/api/v1/goals/{goal_a['id']}")).status_code == 404
    assert (
        await client.patch(
            f"/api/v1/goals/{goal_a['id']}",
            json={"name": "Hijacked"},
            headers={"X-CSRF-Token": session_b.csrf_token},
        )
    ).status_code == 404


async def test_transaction_cannot_reference_another_households_debt(
    client: AsyncClient, db_session: AsyncSession, fake_redis: Redis
) -> None:
    """transactions.debt_id is a new client-supplied FK reference, same IDOR
    class as account_id/category_id -- must be validated against the
    caller's own household, not just accepted and stored.
    """
    _, _, _, session_a = await seed_household(
        db_session, fake_redis, household_name="Household A", owner_email="ownera6@example.com"
    )
    _, _, _, session_b = await seed_household(
        db_session, fake_redis, household_name="Household B", owner_email="ownerb6@example.com"
    )

    apply_session_cookies(client, session_a)
    debt_resp = await client.post(
        "/api/v1/debts",
        json={
            "name": "A's Card",
            "type": "credit_card",
            "original_balance_cents": 10000,
            "current_balance_cents": 10000,
            "apr_bps": 1999,
            "min_payment_cents": 2500,
            "due_day": 15,
        },
        headers={"X-CSRF-Token": session_a.csrf_token},
    )
    debt_a_id = debt_resp.json()["id"]

    apply_session_cookies(client, session_b)
    account_resp = await client.post(
        "/api/v1/accounts",
        json={
            "name": "B's Checking",
            "type": "checking",
            "balance_cents": 0,
            "color": "#336699",
            "icon": "bank",
        },
        headers={"X-CSRF-Token": session_b.csrf_token},
    )
    account_b_id = account_resp.json()["id"]

    create_resp = await client.post(
        "/api/v1/transactions",
        json={
            "account_id": account_b_id,
            "date": "2026-01-15",
            "amount_cents": -500,
            "description": "Cross-household debt attempt",
            "debt_id": debt_a_id,
        },
        headers={"X-CSRF-Token": session_b.csrf_token},
    )
    assert create_resp.status_code == 404

    valid_resp = await client.post(
        "/api/v1/transactions",
        json={
            "account_id": account_b_id,
            "date": "2026-01-15",
            "amount_cents": -500,
            "description": "B's real transaction",
        },
        headers={"X-CSRF-Token": session_b.csrf_token},
    )
    assert valid_resp.status_code == 201
    transaction_b_id = valid_resp.json()["id"]

    update_resp = await client.patch(
        f"/api/v1/transactions/{transaction_b_id}",
        json={"debt_id": debt_a_id},
        headers={"X-CSRF-Token": session_b.csrf_token},
    )
    assert update_resp.status_code == 404
