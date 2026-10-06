from types import SimpleNamespace

from telepat.llm.claude import (
    _extract_claude_text,
    _normalize_claude_usage,
)
from telepat.llm.gemini import _normalize_gemini_usage
from telepat.llm.groq import _normalize_groq_usage
from telepat.llm.openai import (
    _extract_response_text,
    _normalize_openai_usage,
)


def test_extract_openai_response_text() -> None:
    data = {
        "output": [
            {
                "type": "message",
                "content": [
                    {"type": "output_text", "text": "Первая часть."},
                    {"type": "output_text", "text": "Вторая часть."},
                ],
            }
        ]
    }

    assert _extract_response_text(data) == "Первая часть.\nВторая часть."


def test_extract_openai_ignores_non_text_items() -> None:
    data = {
        "output": [
            {"type": "reasoning", "content": []},
            {
                "type": "message",
                "content": [{"type": "refusal", "refusal": "no"}],
            },
        ]
    }

    assert _extract_response_text(data) == ""


def test_extract_claude_text() -> None:
    data = {
        "content": [
            {"type": "text", "text": "Один."},
            {"type": "tool_use", "id": "x"},
            {"type": "text", "text": "Два."},
        ]
    }

    assert _extract_claude_text(data) == "Один.\nДва."



def test_openai_usage_normalizes_cached_input() -> None:
    usage = _normalize_openai_usage(
        {
            "input_tokens": 1000,
            "output_tokens": 100,
            "input_tokens_details": {"cached_tokens": 400},
        }
    )

    assert usage.input_tokens == 600
    assert usage.cached_input_tokens == 400
    assert usage.output_tokens == 100


def test_groq_usage_normalizes_cached_input() -> None:
    usage = _normalize_groq_usage(
        {
            "prompt_tokens": 900,
            "completion_tokens": 120,
            "prompt_tokens_details": {"cached_tokens": 300},
        }
    )

    assert usage.input_tokens == 600
    assert usage.cached_input_tokens == 300
    assert usage.output_tokens == 120


def test_gemini_usage_normalizes_cache_and_thinking() -> None:
    usage = _normalize_gemini_usage(
        SimpleNamespace(
            total_input_tokens=800,
            total_cached_tokens=250,
            total_output_tokens=150,
            total_thought_tokens=75,
        )
    )

    assert usage.input_tokens == 550
    assert usage.cached_input_tokens == 250
    assert usage.output_tokens == 150
    assert usage.thought_tokens == 75


def test_claude_usage_keeps_cache_read_and_write_separate() -> None:
    usage = _normalize_claude_usage(
        {
            "input_tokens": 500,
            "output_tokens": 100,
            "cache_read_input_tokens": 300,
            "cache_creation_input_tokens": 200,
        }
    )

    assert usage.input_tokens == 500
    assert usage.cached_input_tokens == 300
    assert usage.cache_write_input_tokens == 200
    assert usage.output_tokens == 100
