from telepat.memory.compact import compact_memory
from telepat.memory.identity import legacy_memory_user_id


def test_legacy_id_is_stable_positive_integer() -> None:
    a = legacy_memory_user_id("same-browser-id")
    b = legacy_memory_user_id("same-browser-id")
    c = legacy_memory_user_id("other-browser-id")

    assert isinstance(a, int)
    assert a > 0
    assert a == b
    assert a != c


def test_compact_memory_limits_payload() -> None:
    memory = compact_memory(
        {
            "context_text": "x" * 10000,
            "facts": [
                {"key": "name", "value": "V" * 1000}
                for _ in range(50)
            ],
            "semantic_context": [{"text": "s" * 2000, "score": 0.9}] * 10,
            "recent_messages": [
                {"role": "user", "content": "m" * 2000}
                for _ in range(20)
            ],
        }
    )

    assert len(memory["context_text"]) <= 5001
    assert len(memory["facts"]) == 30
    assert len(memory["semantic_context"]) == 5
    assert len(memory["recent_messages"]) == 10
