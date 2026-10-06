from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient

from telepat.memory_api.api import create_memory_app
from telepat.memory_api.store import SQLiteMemoryStore


def _store(tmp_path: Path, **kwargs) -> SQLiteMemoryStore:
    return SQLiteMemoryStore(
        tmp_path / "memory.sqlite3",
        **kwargs,
    )


def test_memory_api_requires_bearer_auth(tmp_path: Path) -> None:
    app = create_memory_app(
        store=_store(tmp_path),
        api_key="secret",
    )
    client = TestClient(app)

    response = client.post(
        "/api/recall",
        json={
            "user_id": 1,
            "message": "hello",
            "level": "simple",
        },
    )
    assert response.status_code == 401

    response = client.post(
        "/api/recall",
        json={
            "user_id": 1,
            "message": "hello",
            "level": "simple",
        },
        headers={"Authorization": "Bearer secret"},
    )
    assert response.status_code == 200


def test_memory_store_recalls_relevant_exchange(
    tmp_path: Path,
) -> None:
    store = _store(tmp_path)
    store.store_exchange(
        user_id=7,
        message="Мне нравится зелёный чай и жасмин.",
        response="Запомнил твоё предпочтение.",
    )
    store.store_exchange(
        user_id=7,
        message="Сегодня обсуждали архитектуру TELEPAT.",
        response="Да, говорили про оркестратор.",
    )

    recalled = store.recall(
        user_id=7,
        message="Какой чай мне нравится?",
        level="medium",
    )

    assert "зелёный чай" in recalled["context_text"]
    assert recalled["semantic_context"]
    assert recalled["recent_messages"]
    assert recalled["recall_ms"] >= 0


def test_memory_store_isolated_by_user(tmp_path: Path) -> None:
    store = _store(tmp_path)
    store.store_exchange(
        user_id=1,
        message="Секрет первого пользователя",
        response="Ответ первому",
    )
    store.store_exchange(
        user_id=2,
        message="Данные второго пользователя",
        response="Ответ второму",
    )

    recalled = store.recall(
        user_id=2,
        message="Что ты помнишь?",
        level="deep",
    )

    assert "Секрет первого пользователя" not in recalled["context_text"]
    assert "Данные второго пользователя" in recalled["context_text"]


def test_memory_store_bounds_history_per_user(
    tmp_path: Path,
) -> None:
    store = _store(
        tmp_path,
        max_exchanges_per_user=20,
    )
    for index in range(30):
        store.store_exchange(
            user_id=9,
            message=f"message {index}",
            response=f"response {index}",
        )

    recalled = store.recall(
        user_id=9,
        message="message",
        level="deep",
    )

    assert "message 0" not in recalled["context_text"]
    assert "message 29" in recalled["context_text"]


def test_memory_store_calls_persistence_hook(tmp_path: Path) -> None:
    calls = {"count": 0}

    def persist() -> None:
        calls["count"] += 1

    store = _store(
        tmp_path,
        commit_callback=persist,
    )
    initial = calls["count"]

    store.store_exchange(
        user_id=3,
        message="hello",
        response="world",
    )

    assert calls["count"] == initial + 1
