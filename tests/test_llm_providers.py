from telepat.llm.claude import _extract_claude_text
from telepat.llm.openai import _extract_response_text


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
