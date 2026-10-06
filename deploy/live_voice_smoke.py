from __future__ import annotations

import asyncio
import json
import os
import urllib.request
from urllib.parse import urlencode, urlsplit, urlunsplit

import modal
import websockets


APP_NAME = "quantareon-telepat"
VOICE_TEST_FUNCTION = "voice_smoke_audio"


def _enabled(name: str, default: str = "0") -> bool:
    return os.getenv(name, default).strip().lower() in {
        "1",
        "true",
        "yes",
        "on",
    }


def websocket_url(http_base: str) -> str:
    parts = urlsplit(http_base.rstrip("/"))
    scheme = "wss" if parts.scheme == "https" else "ws"
    path = parts.path.rstrip("/") + "/ws/voice"
    suffix = (
        os.getenv("TELEPAT_BUILD_SHA", "local")
        .strip()
        .replace("/", "-")[:24]
        or "local"
    )
    query = urlencode(
        {
            "user_id": f"telepat-live-voice-smoke-{suffix}",
            "session_id": f"telepat-live-voice-session-{suffix}",
            "language": "ru",
        }
    )
    return urlunsplit((scheme, parts.netloc, path, query, ""))


def _provider_status(http_base: str) -> dict[str, bool]:
    req = urllib.request.Request(
        http_base.rstrip("/") + "/health/providers",
        headers={"Accept": "application/json"},
        method="GET",
    )
    with urllib.request.urlopen(req, timeout=20) as response:
        data = json.loads(response.read().decode("utf-8"))
    return {
        str(key): bool(value)
        for key, value in data.items()
    }


def _load_voice_test_pcm() -> bytes:
    generator = modal.Function.from_name(
        APP_NAME,
        VOICE_TEST_FUNCTION,
    )
    audio = generator.remote()
    if not isinstance(audio, bytes) or not audio:
        raise RuntimeError("TELEPAT voice smoke PCM generator returned no audio")
    return audio


async def _stream_pcm_realtime(ws, audio: bytes) -> None:
    bytes_per_second = 32000
    frame_bytes = 3200  # 100 ms of PCM16 mono 16 kHz.

    payload = audio + (b"\x00\x00" * 8000)  # trailing 500 ms silence
    for offset in range(0, len(payload), frame_bytes):
        frame = payload[offset:offset + frame_bytes]
        if not frame:
            continue
        await ws.send(frame)
        await asyncio.sleep(len(frame) / bytes_per_second)


async def _exercise_real_voice_turn(
    ws,
    *,
    exercise_barge_in: bool = False,
) -> dict[str, object]:
    pcm = await asyncio.to_thread(_load_voice_test_pcm)
    await _stream_pcm_realtime(ws, pcm)
    await ws.send(json.dumps({"type": "finalize"}))

    transcript = ""
    reply = ""
    llm_provider = ""
    tts_provider = ""
    turn_id = None
    audio_bytes = 0
    accepting_audio = False

    async with asyncio.timeout(90):
        while True:
            raw = await ws.recv()

            if isinstance(raw, bytes):
                if accepting_audio:
                    audio_bytes += len(raw)
                continue

            event = json.loads(raw)
            kind = event.get("type")

            if kind == "error":
                raise RuntimeError(
                    "Voice E2E failed at "
                    + str(event.get("stage") or "unknown")
                )

            if kind == "session_end":
                raise RuntimeError(
                    "Voice E2E session ended before audio response: "
                    + str(event.get("reason") or "unknown")
                )

            if kind == "transcript" and event.get("final") is True:
                transcript = str(event.get("text") or "").strip()
                turn_id = event.get("turn_id")

            elif kind == "reply":
                reply = str(event.get("text") or "").strip()
                llm_provider = str(event.get("provider") or "")
                if turn_id is None:
                    turn_id = event.get("turn_id")

            elif kind == "audio_start":
                tts_provider = str(event.get("provider") or "")
                accepting_audio = True
                if turn_id is None:
                    turn_id = event.get("turn_id")

            elif kind == "audio_end":
                accepting_audio = False
                end_turn_id = event.get("turn_id")
                if turn_id is not None and end_turn_id is not None:
                    assert int(end_turn_id) == int(turn_id), event
                break

    assert transcript, "Deepgram returned no final transcript"
    assert reply, "Voice orchestrator returned no reply"
    assert llm_provider and llm_provider != "mock", llm_provider
    assert tts_provider, "TTS provider missing"
    assert audio_bytes > 0, "Voice response contained no binary audio"

    barge_in = False
    if exercise_barge_in:
        # Do not acknowledge playback_end yet. TELEPAT must still consider the
        # first turn audible when fresh real speech reaches Deepgram.
        await _stream_pcm_realtime(ws, pcm)
        await ws.send(json.dumps({"type": "finalize"}))

        async with asyncio.timeout(45):
            while True:
                raw = await ws.recv()
                if isinstance(raw, bytes):
                    continue
                event = json.loads(raw)
                kind = event.get("type")
                if kind == "error":
                    raise RuntimeError(
                        "Voice barge-in failed at "
                        + str(event.get("stage") or "unknown")
                    )
                if kind == "barge_in":
                    interrupted = event.get("turn_id")
                    if turn_id is not None and interrupted is not None:
                        assert int(interrupted) == int(turn_id), event
                    barge_in = True
                    break

        assert barge_in, "Real speech did not trigger barge_in"
    else:
        await ws.send(
            json.dumps(
                {
                    "type": "playback_end",
                    "turn_id": turn_id,
                }
            )
        )

    return {
        "e2e_turn": True,
        "transcript_chars": len(transcript),
        "reply_chars": len(reply),
        "llm_provider": llm_provider,
        "tts_provider": tts_provider,
        "audio_bytes": audio_bytes,
        "turn_id": turn_id,
        "barge_in": barge_in,
    }


async def _check_once(
    url: str,
    providers: dict[str, bool],
) -> dict[str, object]:
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

        result: dict[str, object] = {
            "websocket": True,
            "deepgram_configured": True,
            "ready": True,
            "ping_pong": True,
        }

        conversation_ready = any(
            providers.get(name)
            for name in ("gemini", "groq", "openai", "claude")
        )

        if (
            providers.get("deepgram")
            and providers.get("yandex_ermil")
            and conversation_ready
        ):
            result.update(
                await _exercise_real_voice_turn(
                    ws,
                    exercise_barge_in=_enabled(
                        "TELEPAT_REAL_BARGE_IN_SMOKE_ENABLED"
                    ),
                )
            )
        else:
            result["e2e_turn"] = False
            result["e2e_skip_reason"] = "required_real_providers_not_configured"

        return result


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
            # Query provider readiness before opening the long-lived WebSocket.
            # The Modal CPU runtime intentionally runs one container while
            # sessions are in-process; a nested HTTP request from inside an
            # active WebSocket can otherwise wait behind that same connection.
            providers = await asyncio.to_thread(_provider_status, base)
            result = await _check_once(url, providers)
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
