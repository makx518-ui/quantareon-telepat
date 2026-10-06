from __future__ import annotations

import asyncio
import json
import os
from urllib.parse import urlencode, urlsplit, urlunsplit

import websockets


def websocket_url(http_base: str) -> str:
    parts = urlsplit(http_base.rstrip("/"))
    scheme = "wss" if parts.scheme == "https" else "ws"
    path = parts.path.rstrip("/") + "/ws/voice"
    query = urlencode(
        {
            "user_id": "telepat-live-voice-smoke",
            "language": "ru",
        }
    )
    return urlunsplit((scheme, parts.netloc, path, query, ""))


async def _check_once(url: str) -> dict[str, object]:
    async with websockets.connect(
        url,
        open_timeout=20,
        close_timeout=10,
        ping_interval=None,
    ) as ws:
        first_raw = await asyncio.wait_for(ws.recv(), timeout=30)
        if not isinstance(first_raw, str):
            raise RuntimeError("Expected JSON control frame from TELEPAT")

        first = json.loads(first_raw)
        kind = first.get("type")

        if kind == "error":
            assert first.get("stage") == "stt", first
            assert "Deepgram" in str(first.get("message") or ""), first
            return {
                "websocket": True,
                "deepgram_configured": False,
                "controlled_error": True,
            }

        assert kind == "ready", first

        await ws.send(json.dumps({"type": "ping"}))
        pong_raw = await asyncio.wait_for(ws.recv(), timeout=10)
        assert isinstance(pong_raw, str)
        pong = json.loads(pong_raw)
        assert pong.get("type") == "pong", pong

        return {
            "websocket": True,
            "deepgram_configured": True,
            "ready": True,
            "ping_pong": True,
        }


async def run() -> None:
    base = os.environ["TELEPAT_ENDPOINT"]
    url = websocket_url(base)
    retries = max(
        1,
        int(os.getenv("TELEPAT_SMOKE_TRANSPORT_RETRIES", "3")),
    )

    last_error: Exception | None = None
    for attempt in range(1, retries + 1):
        try:
            result = await _check_once(url)
            print(json.dumps(result))
            return
        except (TimeoutError, OSError) as exc:
            last_error = exc
            if attempt >= retries:
                break
            await asyncio.sleep(0.5 * attempt)

    assert last_error is not None
    raise last_error


if __name__ == "__main__":
    asyncio.run(run())
