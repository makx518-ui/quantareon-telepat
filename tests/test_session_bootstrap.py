from fastapi.testclient import TestClient

from telepat.api.main import app
from telepat.astro.models import AstroCalculation, AstroSummary
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
