from telepat.observability.metrics import MetricsRegistry


def test_metrics_registry_reports_bounded_latency_aggregates() -> None:
    metrics = MetricsRegistry(sample_limit=10)

    metrics.record("llm", 10, ok=True, provider="mock")
    metrics.record("llm", 20, ok=True, provider="mock")
    metrics.record("llm", 30, ok=False, provider="mock")

    snapshot = metrics.snapshot()["llm"]

    assert snapshot["count"] == 3
    assert snapshot["errors"] == 1
    assert snapshot["success_rate"] == 0.6667
    assert snapshot["avg_ms"] == 20.0
    assert snapshot["p50_ms"] == 20.0
    assert snapshot["p95_ms"] == 30.0
    assert snapshot["max_ms"] == 30.0
    assert snapshot["providers"] == {"mock": 3}


def test_metrics_registry_keeps_only_bounded_latency_samples() -> None:
    metrics = MetricsRegistry(sample_limit=10)

    for index in range(25):
        metrics.record("turn_total", index, ok=True)

    snapshot = metrics.snapshot()["turn_total"]

    assert snapshot["count"] == 25
    assert snapshot["sample_size"] == 10
    assert snapshot["max_ms"] == 24.0
