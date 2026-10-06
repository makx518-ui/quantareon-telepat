from fastapi.testclient import TestClient

from telepat.api.main import app
from telepat.core.session_service import session_store
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



def test_session_usage_requires_matching_user() -> None:
    created = client.post(
        "/chat",
        json={
            "message": "Привет",
            "language": "ru",
            "user_id": "usage-owner",
            "session_id": "usage-session",
        },
    )
    assert created.status_code == 200

    ok = client.get(
        "/session/usage",
        params={
            "session_id": "usage-session",
            "user_id": "usage-owner",
        },
    )
    assert ok.status_code == 200
    usage = ok.json()["usage"]
    assert usage["calls"] >= 1
    assert usage["providers"]["mock"] >= 1
    assert usage["priced_cost_usd"] == 0.0

    wrong_user = client.get(
        "/session/usage",
        params={
            "session_id": "usage-session",
            "user_id": "different-user",
        },
    )
    assert wrong_user.status_code == 404
    assert wrong_user.json()["detail"] == "session_not_found"



def test_chat_idempotent_retry_returns_cached_response() -> None:
    payload = {
        "message": "Один и тот же запрос",
        "request_id": "idem-api-same",
        "language": "ru",
        "user_id": "idem-api-user",
        "session_id": "idem-api-session",
    }

    first = client.post("/chat", json=payload)
    second = client.post("/chat", json=payload)

    assert first.status_code == 200
    assert second.status_code == 200
    assert second.json() == first.json()

    session = session_store.get("idem-api-session")
    assert session is not None
    assert len(session.history) == 2


def test_chat_idempotency_conflict_returns_409() -> None:
    base = {
        "request_id": "idem-api-conflict",
        "language": "ru",
        "user_id": "idem-conflict-user",
        "session_id": "idem-conflict-session",
    }

    first = client.post(
        "/chat",
        json={
            **base,
            "message": "Первый текст",
        },
    )
    second = client.post(
        "/chat",
        json={
            **base,
            "message": "Другой текст",
        },
    )

    assert first.status_code == 200
    assert second.status_code == 409
    assert second.json()["detail"] == "idempotency_key_conflict"

    session = session_store.get("idem-conflict-session")
    assert session is not None
    assert len(session.history) == 2
    assert session.history[0].content == "Первый текст"



def test_chat_returns_503_when_llm_reply_fails_response_policy(
    monkeypatch,
) -> None:
    async def blank_reply(*args, **kwargs):
        return "   \n\n ", "mock"

    monkeypatch.setattr(llm_router, "generate", blank_reply)

    response = client.post(
        "/chat",
        json={
            "message": "Проверка пустого ответа",
            "language": "ru",
            "user_id": "policy-api-user",
            "session_id": "policy-api-session",
        },
    )

    assert response.status_code == 503
    assert response.json()["detail"] == "conversation_provider_unavailable"

    session = session_store.get("policy-api-session")
    assert session is not None
    assert session.history == []
