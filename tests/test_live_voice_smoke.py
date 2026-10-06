import asyncio

from deploy import live_voice_smoke


def test_live_voice_smoke_retries_transient_open_timeout(monkeypatch) -> None:
    calls = {"count": 0}

    async def fake_check(url: str):
        calls["count"] += 1
        if calls["count"] < 3:
            raise TimeoutError("opening handshake timeout")
        return {
            "websocket": True,
            "deepgram_configured": False,
            "controlled_error": True,
        }

    monkeypatch.setattr(live_voice_smoke, "_check_once", fake_check)
    monkeypatch.setattr(
        live_voice_smoke.asyncio,
        "sleep",
        lambda _delay: asyncio.sleep(0),
    )
    monkeypatch.setenv(
        "TELEPAT_ENDPOINT",
        "https://example.invalid",
    )
    monkeypatch.setenv("TELEPAT_SMOKE_TRANSPORT_RETRIES", "3")

    asyncio.run(live_voice_smoke.run())

    assert calls["count"] == 3
