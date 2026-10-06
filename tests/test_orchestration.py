import gc
import asyncio

import pytest

from telepat.core.models import ChatRequest
from telepat.core.orchestrator import Orchestrator, orchestrator
from telepat.core.plan import build_plan
from telepat.core.session_manager import session_manager
from telepat.llm.router import ConversationUnavailableError, llm_router


def test_astro_plan_uses_astro_and_memory() -> None:
    plan = build_plan("astropsychology")
    assert plan.use_astro is True
    assert plan.use_memory is True
    assert plan.psychology_level == "full"
    assert plan.avatar_state == "thinking"


def test_casual_plan_avoids_unnecessary_astro() -> None:
    plan = build_plan("casual_conversation")
    assert plan.use_astro is False
    assert plan.psychology_level == "light"
    assert plan.avatar_state == "idle"


def test_explicit_memory_plan_is_deep_memory_without_astro() -> None:
    plan = build_plan("factual_user_memory")
    assert plan.use_memory is True
    assert plan.use_astro is False
    assert plan.response_mode == "memory"



@pytest.mark.asyncio
async def test_failed_llm_turn_is_not_committed_to_session(monkeypatch) -> None:
    async def unavailable(*args, **kwargs):
        raise ConversationUnavailableError("provider outage")

    monkeypatch.setattr(llm_router, "generate", unavailable)

    request = ChatRequest(
        message="Повтори после сбоя",
        user_id="orchestrator-failure-user",
        session_id="orchestrator-failure-session",
        language="ru",
    )

    with pytest.raises(ConversationUnavailableError):
        await orchestrator.handle_chat(request)

    session = session_manager.get("orchestrator-failure-session")
    assert session is not None
    assert session.history == []



@pytest.mark.asyncio
async def test_orchestrator_drains_tracked_background_tasks() -> None:
    local = Orchestrator()
    completed: list[str] = []

    async def work() -> None:
        await asyncio.sleep(0)
        completed.append("done")

    task = local._spawn_background(work())

    assert task in local._background_tasks

    await local.drain_background()
    await asyncio.sleep(0)

    assert task.done()
    assert completed == ["done"]
    assert local._background_tasks == set()



@pytest.mark.asyncio
async def test_same_session_turns_are_serialized(monkeypatch) -> None:
    local = Orchestrator()
    active = 0
    max_active = 0

    async def slow_generate(context, **kwargs):
        nonlocal active, max_active
        active += 1
        max_active = max(max_active, active)
        await asyncio.sleep(0.02)
        active -= 1
        return f"reply:{context.current_message}", "mock"

    monkeypatch.setattr(llm_router, "generate", slow_generate)

    first = ChatRequest(
        message="one",
        user_id="lock-user",
        session_id="same-lock-session",
        language="ru",
    )
    second = ChatRequest(
        message="two",
        user_id="lock-user",
        session_id="same-lock-session",
        language="ru",
    )

    replies = await asyncio.gather(
        local.handle_chat(first),
        local.handle_chat(second),
    )

    assert max_active == 1
    assert [item.reply for item in replies] == [
        "reply:one",
        "reply:two",
    ]

    session = session_manager.get("same-lock-session")
    assert session is not None
    assert [turn.content for turn in session.history[-4:]] == [
        "one",
        "reply:one",
        "two",
        "reply:two",
    ]


@pytest.mark.asyncio
async def test_different_sessions_can_run_concurrently(monkeypatch) -> None:
    local = Orchestrator()
    active = 0
    max_active = 0
    both_started = asyncio.Event()

    async def slow_generate(context, **kwargs):
        nonlocal active, max_active
        active += 1
        max_active = max(max_active, active)
        if active >= 2:
            both_started.set()
        try:
            await asyncio.wait_for(both_started.wait(), timeout=0.2)
        finally:
            active -= 1
        return "reply", "mock"

    monkeypatch.setattr(llm_router, "generate", slow_generate)

    await asyncio.gather(
        local.handle_chat(
            ChatRequest(
                message="one",
                user_id="parallel-a",
                session_id="parallel-session-a",
                language="ru",
            )
        ),
        local.handle_chat(
            ChatRequest(
                message="two",
                user_id="parallel-b",
                session_id="parallel-session-b",
                language="ru",
            )
        ),
    )

    assert max_active == 2



@pytest.mark.asyncio
async def test_idle_session_turn_lock_is_released() -> None:
    local = Orchestrator()

    lock = await local._turn_lock("ephemeral-session")
    assert "ephemeral-session" in local._session_locks

    del lock
    gc.collect()
    await asyncio.sleep(0)

    assert "ephemeral-session" not in local._session_locks



@pytest.mark.asyncio
async def test_same_request_id_is_idempotent(monkeypatch) -> None:
    local = Orchestrator()
    calls = 0

    async def generate_once(context, **kwargs):
        nonlocal calls
        calls += 1
        return "stable reply", "mock"

    monkeypatch.setattr(llm_router, "generate", generate_once)

    request = ChatRequest(
        message="Повтори безопасно",
        request_id="idem-1",
        user_id="idem-user",
        session_id="idem-session",
        language="ru",
    )

    first = await local.handle_chat(request)
    second = await local.handle_chat(request)

    assert calls == 1
    assert first == second
    assert first.request_id == "idem-1"

    session = session_manager.get("idem-session")
    assert session is not None
    assert [turn.content for turn in session.history[-2:]] == [
        "Повтори безопасно",
        "stable reply",
    ]


@pytest.mark.asyncio
async def test_concurrent_duplicate_request_id_calls_llm_once(
    monkeypatch,
) -> None:
    local = Orchestrator()
    calls = 0

    async def slow_generate(context, **kwargs):
        nonlocal calls
        calls += 1
        await asyncio.sleep(0.02)
        return "one reply", "mock"

    monkeypatch.setattr(llm_router, "generate", slow_generate)

    request = ChatRequest(
        message="Один запрос",
        request_id="idem-concurrent",
        user_id="idem-concurrent-user",
        session_id="idem-concurrent-session",
        language="ru",
    )

    first, second = await asyncio.gather(
        local.handle_chat(request),
        local.handle_chat(request),
    )

    assert calls == 1
    assert first == second
