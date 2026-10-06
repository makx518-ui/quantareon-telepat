from fastapi.testclient import TestClient

from telepat.api.main import app
from telepat.llm.router import ConversationUnavailableError, llm_router
from telepat.security.rate_limit import rate_limiter


client = TestClient(app)


def test_chat_creates_session() -> None:
    response = client.post(
        "/chat",
        json={"message": "Привет", "language": "ru"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["reply"]
    assert data["session_id"]
    assert data["user_id"]
    assert data["provider"] == "mock"


def test_chat_reuses_session() -> None:
    first = client.post("/chat", json={"message": "Привет", "language": "ru"}).json()
    second = client.post(
        "/chat",
        json={
            "message": "Мне тревожно, что делать?",
            "language": "ru",
            "session_id": first["session_id"],
            "user_id": first["user_id"],
        },
    ).json()
    assert second["session_id"] == first["session_id"]
    assert second["user_id"] == first["user_id"]
    assert second["intent"] == "personal_reflection"



def test_chat_returns_503_when_real_llm_is_unavailable(monkeypatch) -> None:
    async def unavailable(*args, **kwargs):
        raise ConversationUnavailableError("provider outage")

    monkeypatch.setattr(llm_router, "generate", unavailable)

    response = client.post(
        "/chat",
        json={"message": "Привет", "language": "ru"},
    )

    assert response.status_code == 503
    assert response.json()["detail"] == "conversation_provider_unavailable"



def test_chat_rate_limit_returns_429(monkeypatch) -> None:
    import telepat.api.main as api_main

    rate_limiter.reset()
    monkeypatch.setattr(api_main, "chat_limit", lambda: 1)

    payload = {
        "message": "Привет",
        "language": "ru",
        "user_id": "rate-limit-user",
    }

    first = client.post("/chat", json=payload)
    second = client.post("/chat", json=payload)

    assert first.status_code == 200
    assert second.status_code == 429
    assert second.json()["detail"] == "chat_rate_limited"
    assert second.headers["retry-after"] == "60"

    rate_limiter.reset()
