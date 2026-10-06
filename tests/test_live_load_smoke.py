import urllib.error

from deploy import live_load_smoke


def test_load_smoke_retries_transient_transport_errors(monkeypatch) -> None:
    calls = {"count": 0}

    def fake_request(method, url, payload=None, *, timeout=30):
        calls["count"] += 1
        if calls["count"] < 3:
            raise urllib.error.URLError("tls timeout")
        return 200, {
            "reply": "ok",
            "provider": "mock",
            "session_id": "load-session-1",
        }

    monkeypatch.setattr(live_load_smoke, "request_json", fake_request)
    monkeypatch.setenv("TELEPAT_CORE_LOAD_TRANSPORT_RETRIES", "3")
    monkeypatch.setattr(live_load_smoke.time, "sleep", lambda _: None)

    result = live_load_smoke.one_chat(
        "https://example.invalid",
        1,
    )

    assert calls["count"] == 3
    assert result["session_id"] == "load-session-1"
    assert result["latency_ms"] >= 0


def test_load_smoke_raises_after_retry_budget(monkeypatch) -> None:
    def always_fail(method, url, payload=None, *, timeout=30):
        raise urllib.error.URLError("tls timeout")

    monkeypatch.setattr(live_load_smoke, "request_json", always_fail)
    monkeypatch.setenv("TELEPAT_CORE_LOAD_TRANSPORT_RETRIES", "2")
    monkeypatch.setattr(live_load_smoke.time, "sleep", lambda _: None)

    try:
        live_load_smoke.one_chat("https://example.invalid", 1)
    except RuntimeError as exc:
        assert "transport failed after 2 attempts" in str(exc)
    else:
        raise AssertionError("expected RuntimeError")



def test_load_smoke_retries_readiness_transport(monkeypatch) -> None:
    calls = {"count": 0}

    def fake_request(method, url, payload=None, *, timeout=30):
        calls["count"] += 1
        if "/health/readiness" in url:
            if calls["count"] < 3:
                raise urllib.error.URLError("tls timeout")
            return 200, {"conversation_ready": True}
        raise AssertionError("unexpected request")

    monkeypatch.setattr(live_load_smoke, "request_json", fake_request)
    monkeypatch.setenv("TELEPAT_ENDPOINT", "https://example.invalid")
    monkeypatch.setenv("TELEPAT_CORE_LOAD_TRANSPORT_RETRIES", "3")
    monkeypatch.setattr(live_load_smoke.time, "sleep", lambda _: None)

    live_load_smoke.main()

    assert calls["count"] == 3



def test_real_provider_load_requires_non_mock(monkeypatch) -> None:
    def fake_request(method, url, payload=None, *, timeout=30):
        return 200, {
            "reply": "ok",
            "provider": "gemini",
            "session_id": "load-session-1",
        }

    monkeypatch.setattr(live_load_smoke, "request_json", fake_request)

    result = live_load_smoke.one_chat(
        "https://example.invalid",
        1,
        expect_real_provider=True,
    )

    assert result["session_id"] == "load-session-1"


def test_real_provider_load_rejects_mock(monkeypatch) -> None:
    def fake_request(method, url, payload=None, *, timeout=30):
        return 200, {
            "reply": "ok",
            "provider": "mock",
            "session_id": "load-session-1",
        }

    monkeypatch.setattr(live_load_smoke, "request_json", fake_request)

    try:
        live_load_smoke.one_chat(
            "https://example.invalid",
            1,
            expect_real_provider=True,
        )
    except RuntimeError as exc:
        assert "unexpectedly used mock" in str(exc)
    else:
        raise AssertionError("expected RuntimeError")
