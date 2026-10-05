import asyncio
import json

from telepat.voice.deepgram import DeepgramStreamingSTT
from telepat.voice.microsoft_tts import microsoft_tts
from telepat.voice.tts_router import TTSRouter
from telepat.voice.yandex_tts import yandex_tts


def test_deepgram_emits_interim_and_final_transcripts() -> None:
    events: list[tuple[str, str]] = []

    stt = DeepgramStreamingSTT(
        language="ru",
        on_interim=lambda text: events.append(("interim", text)),
        on_transcript=lambda text: events.append(("final", text)),
    )

    interim = {
        "type": "Results",
        "is_final": False,
        "speech_final": False,
        "channel": {
            "alternatives": [
                {"transcript": "Приве", "confidence": 0.55}
            ]
        },
    }
    final = {
        "type": "Results",
        "is_final": True,
        "speech_final": True,
        "channel": {
            "alternatives": [
                {"transcript": "Привет", "confidence": 0.96}
            ]
        },
    }

    asyncio.run(stt._handle_message(json.dumps(interim)))
    asyncio.run(stt._handle_message(json.dumps(final)))

    assert events == [
        ("interim", "Приве"),
        ("final", "Привет"),
    ]


def test_deepgram_ru_uses_nova3_streaming_options() -> None:
    stt = DeepgramStreamingSTT(language="ru")
    url = stt._url()

    assert "model=nova-3" in url
    assert "language=ru" in url
    assert "interim_results=true" in url
    assert "vad_events=true" in url


def test_ru_tts_falls_back_to_microsoft(monkeypatch) -> None:
    monkeypatch.setattr(yandex_tts, "api_key", "test-key")
    monkeypatch.setattr(yandex_tts, "iam_token", "")
    monkeypatch.setattr(microsoft_tts, "key", "test-key")
    monkeypatch.setattr(microsoft_tts, "region", "test-region")

    async def fail_yandex(text: str, *, language: str = "ru") -> bytes:
        raise RuntimeError("temporary yandex failure")

    async def microsoft_ok(text: str, *, language: str = "en") -> bytes:
        return b"mp3-audio"

    monkeypatch.setattr(yandex_tts, "synthesize", fail_yandex)
    monkeypatch.setattr(microsoft_tts, "synthesize", microsoft_ok)

    audio, provider = asyncio.run(
        TTSRouter().synthesize("Привет", language="ru")
    )

    assert audio == b"mp3-audio"
    assert provider == "microsoft-andrew"
