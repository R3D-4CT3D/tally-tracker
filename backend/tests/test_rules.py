import time
import uuid
from typing import Any

from httpx import AsyncClient

from app.models.rule import Rule
from app.services.rules import _regex_search_with_timeout, apply_rules
from tests.conftest import SETUP_PAYLOAD


def _csrf_headers(client: AsyncClient) -> dict[str, str]:
    token = client.cookies.get("tally_csrf")
    assert token is not None
    return {"X-CSRF-Token": token}


async def _get_category_id(client: AsyncClient, name: str) -> str:
    resp = await client.get("/api/v1/categories")
    category_id: str = next(c["id"] for c in resp.json() if c["name"] == name)
    return category_id


async def _create_rule(client: AsyncClient, category_id: str, **overrides: Any) -> dict[str, Any]:
    payload = {
        "match_type": "contains",
        "match_value": "coffee",
        "set_category_id": category_id,
        **overrides,
    }
    resp = await client.post("/api/v1/rules", json=payload, headers=_csrf_headers(client))
    assert resp.status_code == 201, resp.text
    result: dict[str, Any] = resp.json()
    return result


async def test_create_and_list_rules_ordered_by_priority(client: AsyncClient) -> None:
    await client.post("/api/v1/setup", json=SETUP_PAYLOAD)
    category_id = await _get_category_id(client, "Dining")

    first = await _create_rule(client, category_id, match_value="coffee")
    second = await _create_rule(client, category_id, match_value="tea")

    listed = await client.get("/api/v1/rules")
    assert listed.status_code == 200
    ids_in_order = [r["id"] for r in listed.json()]
    assert ids_in_order == [first["id"], second["id"]]
    assert listed.json()[0]["priority"] < listed.json()[1]["priority"]


def test_apply_rules_first_match_wins() -> None:
    account_id = uuid.uuid4()
    dining_id = uuid.uuid4()
    misc_id = uuid.uuid4()

    # Both rules would match "Coffee Shop" -- the earlier one in priority
    # order must win, regardless of which is more specific.
    rule_dining = Rule(
        priority=0,
        match_type="contains",
        match_value="coffee",
        set_category_id=dining_id,
        enabled=True,
    )
    rule_misc = Rule(
        priority=1,
        match_type="contains",
        match_value="coffee shop",
        set_category_id=misc_id,
        enabled=True,
    )

    matched = apply_rules(
        [rule_dining, rule_misc],
        description="Coffee Shop",
        amount_cents=-450,
        account_id=account_id,
        timeout=0.05,
    )
    assert matched is rule_dining


def test_apply_rules_skips_disabled_rules() -> None:
    account_id = uuid.uuid4()
    category_id = uuid.uuid4()
    disabled_rule = Rule(
        priority=0,
        match_type="contains",
        match_value="coffee",
        set_category_id=category_id,
        enabled=False,
    )
    enabled_rule = Rule(
        priority=1,
        match_type="contains",
        match_value="coffee",
        set_category_id=category_id,
        enabled=True,
    )

    matched = apply_rules(
        [disabled_rule, enabled_rule],
        description="Coffee Shop",
        amount_cents=-450,
        account_id=account_id,
        timeout=0.05,
    )
    assert matched is enabled_rule


def test_apply_rules_respects_amount_range() -> None:
    account_id = uuid.uuid4()
    category_id = uuid.uuid4()
    rule = Rule(
        priority=0,
        match_type="contains",
        match_value="payment",
        set_category_id=category_id,
        amount_min=-10000,
        amount_max=-100,
        enabled=True,
    )

    in_range = apply_rules(
        [rule], description="Loan Payment", amount_cents=-5000, account_id=account_id, timeout=0.05
    )
    out_of_range = apply_rules(
        [rule], description="Loan Payment", amount_cents=-50, account_id=account_id, timeout=0.05
    )
    assert in_range is rule
    assert out_of_range is None


def test_apply_rules_respects_account_restriction() -> None:
    restricted_account = uuid.uuid4()
    other_account = uuid.uuid4()
    category_id = uuid.uuid4()
    rule = Rule(
        priority=0,
        match_type="contains",
        match_value="coffee",
        set_category_id=category_id,
        account_id=restricted_account,
        enabled=True,
    )

    matches_own_account = apply_rules(
        [rule], description="Coffee", amount_cents=-100, account_id=restricted_account, timeout=0.05
    )
    matches_other_account = apply_rules(
        [rule], description="Coffee", amount_cents=-100, account_id=other_account, timeout=0.05
    )
    assert matches_own_account is rule
    assert matches_other_account is None


async def test_match_type_starts_with(client: AsyncClient) -> None:
    await client.post("/api/v1/setup", json=SETUP_PAYLOAD)
    category_id = await _get_category_id(client, "Dining")
    rule = await _create_rule(
        client, category_id, match_type="starts_with", match_value="starbucks"
    )
    assert rule["match_type"] == "starts_with"


async def test_invalid_match_type_rejected(client: AsyncClient) -> None:
    await client.post("/api/v1/setup", json=SETUP_PAYLOAD)
    category_id = await _get_category_id(client, "Dining")
    # Pydantic's Literal["contains", "starts_with", "regex"] rejects this
    # before it ever reaches app.services.rules._validate_match_pattern --
    # a 422, not the service layer's 400 (that guard exists for the case
    # where a match_type/match_value pair becomes invalid together, e.g. an
    # oversized or malformed regex, not an out-of-enum match_type).
    resp = await client.post(
        "/api/v1/rules",
        json={"match_type": "fuzzy", "match_value": "x", "set_category_id": category_id},
        headers=_csrf_headers(client),
    )
    assert resp.status_code == 422


async def test_invalid_regex_rejected_at_creation(client: AsyncClient) -> None:
    await client.post("/api/v1/setup", json=SETUP_PAYLOAD)
    category_id = await _get_category_id(client, "Dining")
    resp = await client.post(
        "/api/v1/rules",
        json={"match_type": "regex", "match_value": "(unclosed", "set_category_id": category_id},
        headers=_csrf_headers(client),
    )
    assert resp.status_code == 400


async def test_valid_regex_rule_created(client: AsyncClient) -> None:
    await client.post("/api/v1/setup", json=SETUP_PAYLOAD)
    category_id = await _get_category_id(client, "Dining")
    rule = await _create_rule(
        client, category_id, match_type="regex", match_value=r"^coffee.*shop$"
    )
    assert rule["match_type"] == "regex"


async def test_rule_rejects_cross_household_account(
    client: AsyncClient, db_session: Any, fake_redis: Any
) -> None:
    from tests.conftest import apply_session_cookies, seed_household

    _, _, _, session_a = await seed_household(
        db_session, fake_redis, household_name="Household A", owner_email="rulea@example.com"
    )
    _, _, _, session_b = await seed_household(
        db_session, fake_redis, household_name="Household B", owner_email="ruleb@example.com"
    )

    apply_session_cookies(client, session_b)
    account_b_resp = await client.post(
        "/api/v1/accounts",
        json={
            "name": "B Checking",
            "type": "checking",
            "balance_cents": 0,
            "color": "#336699",
            "icon": "bank",
        },
        headers={"X-CSRF-Token": session_b.csrf_token},
    )
    account_b_id = account_b_resp.json()["id"]

    apply_session_cookies(client, session_a)
    category_a_id = (await client.get("/api/v1/categories")).json()[0]["id"]
    resp = await client.post(
        "/api/v1/rules",
        json={
            "match_type": "contains",
            "match_value": "x",
            "set_category_id": category_a_id,
            "account_id": account_b_id,
        },
        headers={"X-CSRF-Token": session_a.csrf_token},
    )
    assert resp.status_code == 404


async def test_rule_rejects_cross_household_category(
    client: AsyncClient, db_session: Any, fake_redis: Any
) -> None:
    from tests.conftest import apply_session_cookies, seed_household

    _, _, _, session_a = await seed_household(
        db_session, fake_redis, household_name="Household A2", owner_email="rulea2@example.com"
    )
    _, _, _, session_b = await seed_household(
        db_session, fake_redis, household_name="Household B2", owner_email="ruleb2@example.com"
    )

    apply_session_cookies(client, session_b)
    category_b_id = (await client.get("/api/v1/categories")).json()[0]["id"]

    apply_session_cookies(client, session_a)
    resp = await client.post(
        "/api/v1/rules",
        json={"match_type": "contains", "match_value": "x", "set_category_id": category_b_id},
        headers={"X-CSRF-Token": session_a.csrf_token},
    )
    assert resp.status_code == 404


async def test_update_rule(client: AsyncClient) -> None:
    await client.post("/api/v1/setup", json=SETUP_PAYLOAD)
    category_id = await _get_category_id(client, "Dining")
    rule = await _create_rule(client, category_id)

    resp = await client.patch(
        f"/api/v1/rules/{rule['id']}",
        json={"match_value": "espresso", "enabled": False},
        headers=_csrf_headers(client),
    )
    assert resp.status_code == 200
    assert resp.json()["match_value"] == "espresso"
    assert resp.json()["enabled"] is False


async def test_delete_rule(client: AsyncClient) -> None:
    await client.post("/api/v1/setup", json=SETUP_PAYLOAD)
    category_id = await _get_category_id(client, "Dining")
    rule = await _create_rule(client, category_id)

    resp = await client.delete(f"/api/v1/rules/{rule['id']}", headers=_csrf_headers(client))
    assert resp.status_code == 204

    listed = await client.get("/api/v1/rules")
    assert listed.json() == []


async def test_reorder_rules(client: AsyncClient) -> None:
    await client.post("/api/v1/setup", json=SETUP_PAYLOAD)
    category_id = await _get_category_id(client, "Dining")
    first = await _create_rule(client, category_id, match_value="coffee")
    second = await _create_rule(client, category_id, match_value="tea")

    resp = await client.post(
        "/api/v1/rules/reorder",
        json={"ordered_ids": [second["id"], first["id"]]},
        headers=_csrf_headers(client),
    )
    assert resp.status_code == 200
    ids_in_order = [r["id"] for r in resp.json()]
    assert ids_in_order == [second["id"], first["id"]]


async def test_reorder_rejects_mismatched_id_set(client: AsyncClient) -> None:
    await client.post("/api/v1/setup", json=SETUP_PAYLOAD)
    category_id = await _get_category_id(client, "Dining")
    await _create_rule(client, category_id)

    resp = await client.post(
        "/api/v1/rules/reorder",
        json={"ordered_ids": ["00000000-0000-0000-0000-000000000000"]},
        headers=_csrf_headers(client),
    )
    assert resp.status_code == 400


def test_redos_pattern_times_out_within_budget() -> None:
    """A classic catastrophic-backtracking pattern must never hang rule
    evaluation -- proves the ReDoS timeout wrapper actually engages, not
    just that it's wired up. See app/services/rules.py's
    _regex_search_with_timeout docstring for why a stdlib-threads-only
    approach was tried and rejected first.
    """
    pattern = "(a|a)+$"
    text = "a" * 30 + "!"

    start = time.monotonic()
    result = _regex_search_with_timeout(pattern, text, timeout=0.05)
    elapsed = time.monotonic() - start

    assert result is False
    assert elapsed < 1.0


def test_normal_regex_still_matches_correctly_and_quickly() -> None:
    start = time.monotonic()
    result = _regex_search_with_timeout(r"coffee", "Local Coffee Shop", timeout=0.05)
    elapsed = time.monotonic() - start

    assert result is True
    assert elapsed < 0.05
