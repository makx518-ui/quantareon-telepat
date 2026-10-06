from telepat.llm.base import ProviderUsage
from telepat.observability.usage import UsageRegistry


def test_usage_registry_counts_tokens_and_explicit_model_cost() -> None:
    registry = UsageRegistry(
        max_sessions=100,
        rates={
            "model-a": {
                "input": 1.0,
                "cached_input": 0.5,
                "output": 2.0,
                "thought": 3.0,
            }
        },
    )

    registry.record(
        "session-a",
        provider="provider-a",
        model="model-a",
        usage=ProviderUsage(
            input_tokens=1000,
            cached_input_tokens=200,
            output_tokens=500,
            thought_tokens=100,
        ),
    )

    snapshot = registry.snapshot("session-a")
    assert snapshot is not None
    assert snapshot["calls"] == 1
    assert snapshot["input_tokens"] == 1000
    assert snapshot["cached_input_tokens"] == 200
    assert snapshot["output_tokens"] == 500
    assert snapshot["thought_tokens"] == 100
    assert snapshot["total_tokens"] == 1600
    assert snapshot["providers"] == {"provider-a": 1}
    assert snapshot["models"] == {"model-a": 1}
    assert snapshot["fully_priced"] is True
    assert snapshot["unpriced_calls"] == 0
    assert snapshot["priced_cost_usd"] == 0.0022


def test_usage_registry_marks_unknown_model_unpriced() -> None:
    registry = UsageRegistry(
        max_sessions=100,
        rates={},
    )

    registry.record(
        "session-a",
        provider="provider-a",
        model="unknown-model",
        usage=ProviderUsage(
            input_tokens=100,
            output_tokens=50,
        ),
    )

    snapshot = registry.snapshot("session-a")
    assert snapshot is not None
    assert snapshot["fully_priced"] is False
    assert snapshot["priced_calls"] == 0
    assert snapshot["unpriced_calls"] == 1
    assert snapshot["priced_cost_usd"] == 0.0


def test_mock_usage_is_zero_cost_and_fully_priced() -> None:
    registry = UsageRegistry(
        max_sessions=100,
        rates={},
    )

    registry.record(
        "session-a",
        provider="mock",
        model="mock",
        usage=ProviderUsage(),
    )

    snapshot = registry.snapshot("session-a")
    assert snapshot is not None
    assert snapshot["fully_priced"] is True
    assert snapshot["priced_calls"] == 1
    assert snapshot["priced_cost_usd"] == 0.0
