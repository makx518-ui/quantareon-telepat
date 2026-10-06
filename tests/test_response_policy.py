import pytest

from telepat.core.response_policy import (
    ResponsePolicyError,
    apply_response_policy,
)


def test_response_policy_rejects_empty_reply() -> None:
    with pytest.raises(ResponsePolicyError):
        apply_response_policy("   \n\n  ")


def test_response_policy_removes_consecutive_duplicate_paragraphs() -> None:
    result = apply_response_policy(
        "Первый абзац.\n\nПовтор.\n\nПовтор.\n\nФинал."
    )

    assert result.text == "Первый абзац.\n\nПовтор.\n\nФинал."
    assert result.duplicate_paragraphs_removed == 1
    assert result.truncated is False


def test_response_policy_truncates_at_sentence_boundary() -> None:
    text = (
        "Первое предложение. "
        "Второе предложение достаточно длинное. "
        "Третье предложение тоже есть."
    )

    result = apply_response_policy(
        text,
        max_chars=55,
    )

    assert result.truncated is True
    assert result.text.endswith("…")
    assert len(result.text) <= 56
    assert result.text.startswith("Первое предложение.")


def test_response_policy_normalizes_line_endings_and_blank_lines() -> None:
    result = apply_response_policy(
        "Строка 1.\r\n\r\n\r\nСтрока 2.   \r\n"
    )

    assert result.text == "Строка 1.\n\nСтрока 2."
