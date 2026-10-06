import asyncio

import pytest

from fastapi.testclient import TestClient

from telepat.api.main import app
from telepat.api.session import prepare_session_astro
from telepat.astro.models import AstroCalculation, AstroSummary, BirthData
from telepat.core.session_manager import session_manager
from telepat.astro.service import astro_service


client = TestClient(app)


def _birth() -> dict[str, object]:
    return {
        "year": 1980,
        "month": 2,
        "day": 10,
        "hour": 12,
        "minute": 30,
        "latitude": 55.7558,
        "longitude": 37.6173,
        "timezone": "Europe/Moscow",
    }


def test_session_bootstrap_creates_identity() -> None:
    response = client.post(
        "/session/bootstrap",
        json={"language": "ru"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["user_id"]
    assert data["session_id"]
    assert data["language"] == "ru"
    assert data["astro_ready"] is False
    assert data["astro_status"] == "missing_birth"


def test_session_bootstrap_reuses_session() -> None:
    first = client.post(
        "/session/bootstrap",
        json={"language": "ru"},
    ).json()

    second = client.post(
        "/session/bootstrap",
        json={
            "language": "ru",
            "user_id": first["user_id"],
            "session_id": first["session_id"],
        },
    ).json()

    assert second["user_id"] == first["user_id"]
    assert second["session_id"] == first["session_id"]


def test_session_bootstrap_prepares_and_caches_astro(monkeypatch) -> None:
    calls = 0

    async def fake_calculate_and_interpret(birth, *, language="ru"):
        nonlocal calls
        calls += 1
        return (
            AstroCalculation(raw_text="fixed astrofractal"),
            AstroSummary(
                overview="Compact overview",
                core_themes=["theme"],
                tensions=["tension"],
                resources=["resource"],
                reflection_questions=["question"],
            ),
        )

    monkeypatch.setattr(
        astro_service,
        "calculate_and_interpret",
        fake_calculate_and_interpret,
    )

    first = client.post(
        "/session/bootstrap",
        json={"language": "ru", "birth": _birth()},
    )
    assert first.status_code == 200
    first_data = first.json()
    assert first_data["astro_ready"] is True
    assert first_data["astro_status"] == "ready"

    second = client.post(
        "/session/bootstrap",
        json={
            "language": "ru",
            "user_id": first_data["user_id"],
            "session_id": first_data["session_id"],
            "birth": _birth(),
        },
    )
    assert second.status_code == 200
    second_data = second.json()
    assert second_data["astro_ready"] is True
    assert second_data["astro_status"] == "cached"

    astro = client.post(
        "/session/astro",
        json={
            "language": "ru",
            "user_id": first_data["user_id"],
            "session_id": first_data["session_id"],
            "birth": _birth(),
        },
    )
    assert astro.status_code == 200
    assert astro.json()["summary"]["overview"] == "Compact overview"
    assert calls == 1



@pytest.mark.asyncio
async def test_concurrent_astro_prepare_runs_interpreter_once(
    monkeypatch,
) -> None:
    calls = 0

    async def fake_calculate_and_interpret(birth, *, language="ru"):
        nonlocal calls
        calls += 1
        await asyncio.sleep(0.02)
        return (
            AstroCalculation(raw_text="fixed astrofractal"),
            AstroSummary(
                overview="Concurrent overview",
                core_themes=["theme"],
                tensions=["tension"],
                resources=["resource"],
                reflection_questions=["question"],
            ),
        )

    monkeypatch.setattr(
        astro_service,
        "calculate_and_interpret",
        fake_calculate_and_interpret,
    )

    session = session_manager.get_or_create(
        session_id="concurrent-astro-session",
        user_id="concurrent-astro-user",
        language="ru",
    )
    birth = BirthData.model_validate(_birth())

    first, second = await asyncio.gather(
        prepare_session_astro(
            session_id=session.session_id,
            birth=birth,
            language="ru",
        ),
        prepare_session_astro(
            session_id=session.session_id,
            birth=birth,
            language="ru",
        ),
    )

    assert calls == 1
    assert {first[1], second[1]} == {False, True}
    assert first[0].overview == "Concurrent overview"
    assert second[0].overview == "Concurrent overview"
