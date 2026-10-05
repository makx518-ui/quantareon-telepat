import asyncio
import json

from telepat.voice.deepgram import DeepgramStreamingSTT, normalize_deepgram_language
from telepat.voice.microsoft_tts import microsoft_tts
from telepat.voice.session import VoiceSession
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




def test_deepgram_waits_for_complete_utterance_across_final_segments() -> None:
    events: list[tuple[str, str]] = []

    stt = DeepgramStreamingSTT(
        language="ru",
        on_interim=lambda text: events.append(("interim", text)),
        on_transcript=lambda text: events.append(("final", text)),
    )

    first_final_segment = {
        "type": "Results",
        "is_final": True,
        "speech_final": False,
        "channel": {
            "alternatives": [
                {"transcript": "Это длинная", "confidence": 0.95}
            ]
        },
    }
    interim_next_segment = {
        "type": "Results",
        "is_final": False,
        "speech_final": False,
        "channel": {
            "alternatives": [
                {"transcript": "фраза пользователя", "confidence": 0.80}
            ]
        },
    }
    last_final_segment = {
        "type": "Results",
        "is_final": True,
        "speech_final": True,
        "channel": {
            "alternatives": [
                {"transcript": "фраза пользователя", "confidence": 0.97}
            ]
        },
    }

    asyncio.run(stt._handle_message(json.dumps(first_final_segment)))
    assert events == []

    asyncio.run(stt._handle_message(json.dumps(interim_next_segment)))
    assert events == [
        ("interim", "Это длинная фраза пользователя"),
    ]

    asyncio.run(stt._handle_message(json.dumps(last_final_segment)))
    assert events[-1] == (
        "final",
        "Это длинная фраза пользователя",
    )
    assert [kind for kind, _ in events].count("final") == 1


def test_deepgram_utterance_end_flushes_accumulated_final_segment() -> None:
    final: list[str] = []

    stt = DeepgramStreamingSTT(
        language="ru",
        on_transcript=final.append,
    )

    segment = {
        "type": "Results",
        "is_final": True,
        "speech_final": False,
        "channel": {
            "alternatives": [
                {"transcript": "Готовая реплика", "confidence": 0.91}
            ]
        },
    }

    asyncio.run(stt._handle_message(json.dumps(segment)))
    assert final == []

    asyncio.run(
        stt._handle_message(json.dumps({"type": "UtteranceEnd"}))
    )
    assert final == ["Готовая реплика"]

def test_deepgram_ru_uses_nova3_streaming_options() -> None:
    stt = DeepgramStreamingSTT(language="ru")
    url = stt._url()

    assert "model=nova-3" in url
    assert "language=ru" in url
    assert "interim_results=true" in url
    assert "vad_events=true" in url




def test_deepgram_preserves_supported_languages() -> None:
    assert normalize_deepgram_language("de") == "de"
    assert normalize_deepgram_language("uk-UA") == "uk"
    assert normalize_deepgram_language("pt_BR") == "pt-BR"
    assert normalize_deepgram_language("zh-HK") == "zh-HK"


def test_deepgram_unknown_language_uses_multilingual() -> None:
    assert normalize_deepgram_language("xx-YY") == "multi"
    assert normalize_deepgram_language("auto") == "multi"

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


class _FakeVoiceWebSocket:
    def __init__(self) -> None:
        self.messages: list[dict] = []

    async def send_json(self, payload: dict) -> None:
        self.messages.append(payload)


def test_barge_in_stops_browser_playback_after_response_task_finished() -> None:
    websocket = _FakeVoiceWebSocket()
    session = VoiceSession(
        websocket,
        user_id="u",
        session_id="s",
        language="ru",
    )
    session._audio_playback_active = True

    asyncio.run(session._on_speech_start())

    assert session._audio_playback_active is False
    assert websocket.messages == [{"type": "barge_in"}]


def test_playback_end_control_clears_server_flag() -> None:
    websocket = _FakeVoiceWebSocket()
    session = VoiceSession(
        websocket,
        user_id="u",
        session_id="s",
        language="ru",
    )
    session._audio_playback_active = True

    asyncio.run(session._handle_control('{"type":"playback_end"}'))

    assert session._audio_playback_active is False
