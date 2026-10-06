from telepat.core.session_manager import SessionManager


def test_session_reuse_preserves_identity() -> None:
    manager = SessionManager(
        ttl_seconds=100,
        max_sessions=10,
        max_history_turns=10,
    )
    first = manager.get_or_create(
        session_id="session-a",
        user_id="user-a",
        language="ru",
    )
    second = manager.get_or_create(
        session_id="session-a",
        user_id="user-a",
        language="en",
    )

    assert first is second
    assert second.user_id == "user-a"
    assert second.language == "en"


def test_session_id_cannot_be_reused_by_different_user() -> None:
    manager = SessionManager(
        ttl_seconds=100,
        max_sessions=10,
        max_history_turns=10,
    )
    first = manager.get_or_create(
        session_id="shared-id",
        user_id="user-a",
        language="ru",
    )
    second = manager.get_or_create(
        session_id="shared-id",
        user_id="user-b",
        language="ru",
    )

    assert first.session_id == "shared-id"
    assert second.user_id == "user-b"
    assert second.session_id != "shared-id"


def test_session_history_is_bounded() -> None:
    manager = SessionManager(
        ttl_seconds=100,
        max_sessions=10,
        max_history_turns=3,
    )
    session = manager.get_or_create(
        session_id="s",
        user_id="u",
        language="ru",
    )

    for index in range(6):
        manager.append("s", "user", f"turn-{index}")

    assert [turn.content for turn in session.history] == [
        "turn-3",
        "turn-4",
        "turn-5",
    ]


def test_stale_session_expires() -> None:
    now = [0.0]

    manager = SessionManager(
        ttl_seconds=10,
        max_sessions=10,
        max_history_turns=10,
        clock=lambda: now[0],
    )
    manager.get_or_create(
        session_id="old",
        user_id="u",
        language="ru",
    )
    assert manager.count() == 1

    now[0] = 11.0

    assert manager.get("old") is None
    assert manager.count() == 0


def test_oldest_session_is_evicted_when_capacity_is_reached() -> None:
    now = [0.0]
    manager = SessionManager(
        ttl_seconds=100,
        max_sessions=2,
        max_history_turns=10,
        clock=lambda: now[0],
    )

    manager.get_or_create(session_id="one", user_id="u1", language="ru")
    now[0] = 1.0
    manager.get_or_create(session_id="two", user_id="u2", language="ru")
    now[0] = 2.0
    manager.get_or_create(session_id="three", user_id="u3", language="ru")

    assert manager.get("one") is None
    assert manager.get("two") is not None
    assert manager.get("three") is not None



def test_idempotency_cache_is_bounded_lru() -> None:
    from telepat.core.models import ChatResponse

    manager = SessionManager(
        ttl_seconds=100,
        max_sessions=10,
        max_history_turns=10,
        max_idempotency_entries=2,
    )
    session = manager.get_or_create(
        session_id="idem",
        user_id="u",
        language="ru",
    )

    def response(request_id: str) -> ChatResponse:
        return ChatResponse(
            reply=request_id,
            request_id=request_id,
            user_id=session.user_id,
            session_id=session.session_id,
            intent="casual_conversation",
        )

    manager.set_idempotent_response(
        "idem", "a", "fp-a", response("a")
    )
    manager.set_idempotent_response(
        "idem", "b", "fp-b", response("b")
    )

    # Touch "a" so "b" becomes least-recently-used.
    assert (
        manager.get_idempotent_response(
            "idem", "a", "fp-a"
        )
        is not None
    )

    manager.set_idempotent_response(
        "idem", "c", "fp-c", response("c")
    )

    assert (
        manager.get_idempotent_response(
            "idem", "a", "fp-a"
        )
        is not None
    )
    assert (
        manager.get_idempotent_response(
            "idem", "b", "fp-b"
        )
        is None
    )
    assert (
        manager.get_idempotent_response(
            "idem", "c", "fp-c"
        )
        is not None
    )



def test_session_id_alone_cannot_reuse_existing_session() -> None:
    manager = SessionManager(
        ttl_seconds=100,
        max_sessions=10,
        max_history_turns=10,
    )
    first = manager.get_or_create(
        session_id="protected-session",
        user_id="owner-user",
        language="ru",
    )

    second = manager.get_or_create(
        session_id="protected-session",
        user_id=None,
        language="ru",
    )

    assert first.session_id == "protected-session"
    assert first.user_id == "owner-user"
    assert second.session_id != first.session_id
    assert second.user_id != first.user_id



def test_idempotency_key_rejects_different_payload_fingerprint() -> None:
    from telepat.core.models import ChatResponse
    from telepat.core.session_store import IdempotencyConflictError

    manager = SessionManager(
        ttl_seconds=100,
        max_sessions=10,
        max_history_turns=10,
        max_idempotency_entries=2,
    )
    session = manager.get_or_create(
        session_id="idem-conflict",
        user_id="u",
        language="ru",
    )
    response = ChatResponse(
        reply="cached",
        request_id="request-1",
        user_id=session.user_id,
        session_id=session.session_id,
        intent="casual_conversation",
    )

    manager.set_idempotent_response(
        session.session_id,
        "request-1",
        "fingerprint-a",
        response,
    )

    try:
        manager.get_idempotent_response(
            session.session_id,
            "request-1",
            "fingerprint-b",
        )
    except IdempotencyConflictError:
        pass
    else:
        raise AssertionError("expected IdempotencyConflictError")
