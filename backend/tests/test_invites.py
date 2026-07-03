import uuid
from datetime import UTC, datetime, timedelta
from typing import Any

from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import generate_invite_token, hash_invite_token
from app.models.invite import Invite
from tests.conftest import SETUP_PAYLOAD


async def _create_invite(client: AsyncClient) -> dict[str, Any]:
    csrf_token = client.cookies.get("tally_csrf")
    assert csrf_token is not None
    resp = await client.post("/api/v1/invites", headers={"X-CSRF-Token": csrf_token})
    assert resp.status_code == 200
    result: dict[str, Any] = resp.json()
    return result


async def test_accept_invite_creates_member(client: AsyncClient) -> None:
    await client.post("/api/v1/setup", json=SETUP_PAYLOAD)
    invite = await _create_invite(client)

    accept = await client.post(
        "/api/v1/invites/accept",
        json={
            "token": invite["token"],
            "email": "partner@example.com",
            "display_name": "Partner",
            "password": "correcthorsebattery456",
        },
    )
    assert accept.status_code == 200
    assert "tally_session" in accept.cookies


async def test_accept_invite_twice_is_rejected(client: AsyncClient) -> None:
    await client.post("/api/v1/setup", json=SETUP_PAYLOAD)
    invite = await _create_invite(client)

    payload = {
        "token": invite["token"],
        "email": "partner@example.com",
        "display_name": "Partner",
        "password": "correcthorsebattery456",
    }
    first = await client.post("/api/v1/invites/accept", json=payload)
    assert first.status_code == 200

    second = await client.post(
        "/api/v1/invites/accept", json={**payload, "email": "someone-else@example.com"}
    )
    assert second.status_code == 400
    assert second.json()["detail"] == "Invalid or expired invite"


async def test_expired_invite_is_rejected(client: AsyncClient, db_session: AsyncSession) -> None:
    await client.post("/api/v1/setup", json=SETUP_PAYLOAD)
    me = (await client.get("/api/v1/auth/me")).json()

    token = generate_invite_token()
    expired_invite = Invite(
        household_id=uuid.UUID(me["household_id"]),
        code_hash=hash_invite_token(token),
        created_by=uuid.UUID(me["user_id"]),
        expires_at=datetime.now(UTC) - timedelta(days=1),
    )
    db_session.add(expired_invite)
    await db_session.commit()

    resp = await client.post(
        "/api/v1/invites/accept",
        json={
            "token": token,
            "email": "too-late@example.com",
            "display_name": "Too Late",
            "password": "correcthorsebattery789",
        },
    )
    assert resp.status_code == 400
    assert resp.json()["detail"] == "Invalid or expired invite"
