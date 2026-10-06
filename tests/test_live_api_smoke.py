import io
import urllib.error

from deploy import live_api_smoke


class _FakeResponse:
    status = 200

    def __init__(self, payload: bytes) -> None:
        self._payload = payload

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

    def read(self) -> bytes:
        return self._payload


def test_live_api_get_retries_transient_transport_errors(monkeypatch) -> None:
    calls = {"count": 0}

    def fake_urlopen(req, timeout=20):
        calls["count"] += 1
        if calls["count"] < 3:
            raise urllib.error.URLError("tls timeout")
        return _FakeResponse(b'{"ok": true}')

    monkeypatch.setattr(live_api_smoke.urllib.request, "urlopen", fake_urlopen)
    monkeypatch.setattr(live_api_smoke.time, "sleep", lambda _: None)
    monkeypatch.setenv("TELEPAT_SMOKE_TRANSPORT_RETRIES", "3")

    status, data = live_api_smoke.request_json(
        "GET",
        "https://example.invalid/health",
    )

    assert calls["count"] == 3
    assert status == 200
    assert data == {"ok": True}


def test_live_api_post_does_not_retry_by_default(monkeypatch) -> None:
    calls = {"count": 0}

    def fake_urlopen(req, timeout=20):
        calls["count"] += 1
        raise urllib.error.URLError("lost response")

    monkeypatch.setattr(live_api_smoke.urllib.request, "urlopen", fake_urlopen)
    monkeypatch.setattr(live_api_smoke.time, "sleep", lambda _: None)

    try:
        live_api_smoke.request_json(
            "POST",
            "https://example.invalid/chat",
            {"message": "hi"},
        )
    except urllib.error.URLError:
        pass
    else:
        raise AssertionError("expected URLError")

    assert calls["count"] == 1
