from datetime import date
from typing import Any

import pytest
from httpx import AsyncClient

from app.services.bill_payments import compute_next_due_date
from tests.conftest import SETUP_PAYLOAD


def _csrf_headers(client: AsyncClient) -> dict[str, str]:
    token = client.cookies.get("tally_csrf")
    assert token is not None
    return {"X-CSRF-Token": token}


async def _create_bill(client: AsyncClient, **overrides: Any) -> dict[str, Any]:
    payload = {
        "name": "Electric",
        "amount_cents": 12000,
        "is_variable": False,
        "frequency": "monthly",
        "due_day": 15,
        "autopay": False,
        "next_due_date": "2026-01-15",
        **overrides,
    }
    resp = await client.post("/api/v1/bills", json=payload, headers=_csrf_headers(client))
    assert resp.status_code == 201, resp.text
    result: dict[str, Any] = resp.json()
    return result


@pytest.mark.parametrize(
    ("frequency", "current", "expected"),
    [
        ("monthly", date(2026, 1, 15), date(2026, 2, 15)),
        ("monthly", date(2026, 1, 31), date(2026, 2, 28)),  # month-end clamp, no drift
        ("quarterly", date(2026, 1, 15), date(2026, 4, 15)),
        ("annual", date(2026, 1, 15), date(2027, 1, 15)),
    ],
)
def test_compute_next_due_date_for_fixed_frequencies(
    frequency: str, current: date, expected: date
) -> None:
    assert compute_next_due_date(current, frequency, None) == expected


def test_compute_next_due_date_for_custom_frequency() -> None:
    assert compute_next_due_date(date(2026, 1, 1), "custom", 10) == date(2026, 1, 11)


def test_compute_next_due_date_custom_without_interval_raises() -> None:
    from app.services.bills import BillValidationError

    with pytest.raises(BillValidationError):
        compute_next_due_date(date(2026, 1, 1), "custom", None)


async def test_create_list_update_archive_bill(client: AsyncClient) -> None:
    await client.post("/api/v1/setup", json=SETUP_PAYLOAD)
    created = await _create_bill(client)
    assert created["frequency"] == "monthly"
    assert created["archived"] is False

    listed = await client.get("/api/v1/bills")
    assert len(listed.json()) == 1

    updated = await client.patch(
        f"/api/v1/bills/{created['id']}",
        json={"amount_cents": 15000},
        headers=_csrf_headers(client),
    )
    assert updated.status_code == 200
    assert updated.json()["amount_cents"] == 15000

    archived = await client.post(
        f"/api/v1/bills/{created['id']}/archive", headers=_csrf_headers(client)
    )
    assert archived.status_code == 200
    assert archived.json()["archived"] is True

    default_list = await client.get("/api/v1/bills")
    assert default_list.json() == []


async def test_custom_frequency_without_interval_days_rejected_on_create(
    client: AsyncClient,
) -> None:
    await client.post("/api/v1/setup", json=SETUP_PAYLOAD)
    resp = await client.post(
        "/api/v1/bills",
        json={
            "name": "Irregular",
            "frequency": "custom",
            "due_day": 1,
            "next_due_date": "2026-01-01",
        },
        headers=_csrf_headers(client),
    )
    assert resp.status_code == 400


async def test_switching_to_custom_frequency_without_interval_days_rejected_on_update(
    client: AsyncClient,
) -> None:
    await client.post("/api/v1/setup", json=SETUP_PAYLOAD)
    bill = await _create_bill(client, frequency="monthly")

    resp = await client.patch(
        f"/api/v1/bills/{bill['id']}",
        json={"frequency": "custom"},
        headers=_csrf_headers(client),
    )
    assert resp.status_code == 400


async def test_switching_away_from_custom_frequency_is_allowed(client: AsyncClient) -> None:
    await client.post("/api/v1/setup", json=SETUP_PAYLOAD)
    bill = await _create_bill(client, frequency="custom", custom_interval_days=14)

    resp = await client.patch(
        f"/api/v1/bills/{bill['id']}",
        json={"frequency": "monthly", "custom_interval_days": None},
        headers=_csrf_headers(client),
    )
    # Switching to monthly while clearing custom_interval_days is fine --
    # custom_interval_days is only required *when* frequency is "custom".
    assert resp.status_code == 200
