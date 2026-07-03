from httpx import AsyncClient

from tests.conftest import SETUP_PAYLOAD


async def test_setup_creates_household_and_logs_in(client: AsyncClient) -> None:
    status_before = await client.get("/api/v1/setup/status")
    assert status_before.json() == {"is_setup": False}

    resp = await client.post("/api/v1/setup", json=SETUP_PAYLOAD)
    assert resp.status_code == 201
    assert "tally_session" in resp.cookies
    assert "tally_csrf" in resp.cookies

    me = await client.get("/api/v1/auth/me")
    assert me.status_code == 200
    body = me.json()
    assert body["role"] == "owner"
    assert body["household_name"] == SETUP_PAYLOAD["household_name"]
    assert body["email"] == SETUP_PAYLOAD["owner_email"]

    status_after = await client.get("/api/v1/setup/status")
    assert status_after.json() == {"is_setup": True}


async def test_setup_runs_only_once(client: AsyncClient) -> None:
    first = await client.post("/api/v1/setup", json=SETUP_PAYLOAD)
    assert first.status_code == 201

    second = await client.post(
        "/api/v1/setup", json={**SETUP_PAYLOAD, "owner_email": "someone-else@example.com"}
    )
    assert second.status_code == 409


async def test_solo_household_has_no_partner_assuming_behavior(client: AsyncClient) -> None:
    await client.post("/api/v1/setup", json=SETUP_PAYLOAD)

    members = await client.get("/api/v1/household/members")
    assert members.status_code == 200
    body = members.json()
    assert len(body) == 1
    assert body[0]["role"] == "owner"
    assert body[0]["email"] == SETUP_PAYLOAD["owner_email"]
