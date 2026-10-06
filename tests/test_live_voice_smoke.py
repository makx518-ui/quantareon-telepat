import asyncio

from deploy import live_voice_smoke


def test_live_voice_smoke_retries_transient_open_timeout(monkeypatch) -> None:
    calls = {"count": 0}

    async def fake_check(url: str, providers: dict[str, bool]):
        calls["count"] += 1
        if calls["count"] < 3:
            raise TimeoutError("opening handshake timeout")
        return {
            "websocket": True,
            "deepgram_configured": False,
            "controlled_error": True,
        }

    monkeypatch.setattr(live_voice_smoke, "_check_once", fake_check)
    async def fake_sleep(_delay: float) -> None:
        return None

    monkeypatch.setattr(
        live_voice_smoke.asyncio,
        "sleep",
        fake_sleep,
    )
    monkeypatch.setenv(
        "TELEPAT_ENDPOINT",
        "https://example.invalid",
    )
    monkeypatch.setenv("TELEPAT_SMOKE_TRANSPORT_RETRIES", "3")

    asyncio.run(live_voice_smoke.run())

    assert calls["count"] == 3



def test_live_voice_smoke_checks_providers_before_websocket(monkeypatch) -> None:
    events: list[str] = []

    def fake_provider_status(base: str) -> dict[str, bool]:
        assert base == "https://example.invalid"
        events.append("providers")
        return {
            "gemini": True,
            "deepgram": True,
            "yandex_ermil": True,
        }

    async def fake_check(
        url: str,
        providers: dict[str, bool],
    ) -> dict[str, object]:
        events.append("websocket")
        assert url.startswith("wss://example.invalid/ws/voice?")
        assert providers["deepgram"] is True
        return {
            "websocket": True,
            "deepgram_configured": True,
            "e2e_turn": True,
        }

    monkeypatch.setattr(
        live_voice_smoke,
        "_provider_status",
        fake_provider_status,
    )
    monkeypatch.setattr(live_voice_smoke, "_check_once", fake_check)
    monkeypatch.setenv(
        "TELEPAT_ENDPOINT",
        "https://example.invalid",
    )
    monkeypatch.setenv("TELEPAT_SMOKE_TRANSPORT_RETRIES", "1")

    asyncio.run(live_voice_smoke.run())

    assert events == ["providers", "websocket"]
