from telepat.diagnostics.provider_probe import _safe_error


def test_safe_error_redacts_secret_environment_values(monkeypatch) -> None:
    monkeypatch.setenv("GEMINI_API_KEY", "secret-value-123456789")
    report = _safe_error(
        RuntimeError("provider rejected secret-value-123456789")
    )

    assert report["error"] == "RuntimeError"
    assert "secret-value-123456789" not in report["detail"]
    assert "***" in report["detail"]
