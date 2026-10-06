import asyncio
import json

import pytest

from telepat.core.models import ChatResponse
from telepat.llm.router import ConversationUnavailableError, llm_router
from telepat.voice.deepgram import DeepgramStreamingSTT, normalize_deepgram_language
from telepat.voice.microsoft_tts import microsoft_tts
from telepat.voice.session import VoiceIdleTimeout, VoiceSession
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



def test_deepgram_tracks_detected_language_from_result() -> None:
    stt = DeepgramStreamingSTT(language="auto")

    payload = {
        "type": "Results",
        "is_final": True,
        "speech_final": True,
        "channel": {
            "alternatives": [
                {
                    "transcript": "Guten Tag",
                    "confidence": 0.99,
                    "languages": ["de-DE"],
                    "words": [
                        {"word": "Guten", "language": "de-DE"},
                        {"word": "Tag", "language": "de-DE"},
                    ],
                }
            ]
        },
    }

    asyncio.run(stt._handle_message(json.dumps(payload)))

    assert stt.detected_language == "de-DE"


def test_deepgram_detects_majority_word_language() -> None:
    best = {
        "words": [
            {"word": "one", "language": "en-US"},
            {"word": "два", "language": "ru"},
            {"word": "три", "language": "ru"},
        ]
    }

    assert DeepgramStreamingSTT._detect_result_language(best) == "ru"


def test_voice_auto_language_uses_detected_language() -> None:
    websocket = _FakeVoiceWebSocket()
    session = VoiceSession(
        websocket,
        user_id="u",
        session_id="s",
        language="auto",
    )
    session.stt.detected_language = "ja-JP"

    asyncio.run(session._on_transcript("こんにちは"))

    assert session._transcripts.get_nowait() == (
        "こんにちは",
        "ja-JP",
        1,
    )


def test_andrew_locale_mapping_covers_nova3_multilingual_core() -> None:
    assert microsoft_tts._locale("ru") == "ru-RU"
    assert microsoft_tts._locale("hi") == "hi-IN"
    assert microsoft_tts._locale("ja") == "ja-JP"
    assert microsoft_tts._locale("nl") == "nl-NL"

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
        self.binary: list[bytes] = []
        self.closed: tuple[int, str] | None = None

    async def send_json(self, payload: dict) -> None:
        self.messages.append(payload)

    async def send_bytes(self, payload: bytes) -> None:
        self.binary.append(payload)

    async def close(
        self,
        code: int = 1000,
        reason: str = "",
    ) -> None:
        self.closed = (code, reason)


def test_barge_in_stops_browser_playback_after_response_task_finished() -> None:
    websocket = _FakeVoiceWebSocket()
    session = VoiceSession(
        websocket,
        user_id="u",
        session_id="s",
        language="ru",
    )
    session._audio_playback_active = True
    session._playback_turn_id = 7

    asyncio.run(session._on_speech_start())

    assert session._audio_playback_active is False
    assert session._playback_turn_id is None
    assert websocket.messages == [
        {"type": "barge_in", "turn_id": 7}
    ]


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



def test_playback_end_for_old_turn_does_not_clear_current_playback() -> None:
    websocket = _FakeVoiceWebSocket()
    session = VoiceSession(
        websocket,
        user_id="u",
        session_id="s",
        language="ru",
    )
    session._audio_playback_active = True
    session._playback_turn_id = 9

    asyncio.run(
        session._handle_control(
            '{"type":"playback_end","turn_id":8}'
        )
    )

    assert session._audio_playback_active is True
    assert session._playback_turn_id == 9

    asyncio.run(
        session._handle_control(
            '{"type":"playback_end","turn_id":9}'
        )
    )

    assert session._audio_playback_active is False
    assert session._playback_turn_id is None


def test_voice_turn_ids_are_monotonic() -> None:
    websocket = _FakeVoiceWebSocket()
    session = VoiceSession(
        websocket,
        user_id="u",
        session_id="s",
        language="ru",
    )

    asyncio.run(session._on_transcript("one"))
    asyncio.run(session._on_transcript("two"))

    first = session._transcripts.get_nowait()
    second = session._transcripts.get_nowait()

    assert first[2] == 1
    assert second[2] == 2


class _BrokenDeepgramSocket:
    def __aiter__(self):
        return self

    async def __anext__(self):
        raise RuntimeError("upstream disconnected")


def test_unexpected_deepgram_disconnect_calls_callback() -> None:
    events: list[str] = []

    stt = DeepgramStreamingSTT(
        language="ru",
        on_disconnect=lambda: events.append("disconnected"),
    )
    stt._ws = _BrokenDeepgramSocket()
    stt._connected = True
    stt._closing = False

    asyncio.run(stt._receive_loop())

    assert events == ["disconnected"]
    assert stt._connected is False


def test_voice_session_closes_browser_when_stt_disconnects() -> None:
    websocket = _FakeVoiceWebSocket()
    session = VoiceSession(
        websocket,
        user_id="u",
        session_id="s",
        language="ru",
    )

    asyncio.run(session._on_stt_disconnect())

    assert websocket.messages == [
        {
            "type": "error",
            "stage": "stt",
            "message": "Deepgram disconnected",
        }
    ]
    assert websocket.closed == (
        1011,
        "upstream stt disconnected",
    )



@pytest.mark.asyncio
async def test_voice_session_close_awaits_background_tasks() -> None:
    websocket = _FakeVoiceWebSocket()
    session = VoiceSession(
        websocket,
        user_id="u",
        session_id="s",
        language="ru",
    )

    response_task = asyncio.create_task(asyncio.sleep(60))
    processor_task = asyncio.create_task(asyncio.sleep(60))
    session._response_task = response_task
    session._processor_task = processor_task
    session._audio_playback_active = True

    await asyncio.sleep(0)
    await session.close()

    assert response_task.done()
    assert processor_task.done()
    assert session._response_task is None
    assert session._processor_task is None
    assert session._audio_playback_active is False
    assert websocket.closed is not None



@pytest.mark.asyncio
async def test_voice_reports_llm_provider_outage(monkeypatch) -> None:
    async def unavailable(*args, **kwargs):
        raise ConversationUnavailableError("provider outage")

    monkeypatch.setattr(llm_router, "generate", unavailable)

    websocket = _FakeVoiceWebSocket()
    session = VoiceSession(
        websocket,
        user_id="voice-outage-user",
        session_id="voice-outage-session",
        language="ru",
    )

    await session._respond("Проверка")

    assert websocket.messages[-1] == {
        "type": "error",
        "stage": "llm",
        "message": "conversation_provider_unavailable",
        "turn_id": 1,
    }



class _IdleVoiceWebSocket(_FakeVoiceWebSocket):
    async def receive(self):
        await asyncio.sleep(60)
        return {"type": "websocket.receive"}


@pytest.mark.asyncio
async def test_voice_idle_timeout_raises_policy_signal() -> None:
    websocket = _IdleVoiceWebSocket()
    session = VoiceSession(
        websocket,
        user_id="u",
        session_id="s",
        language="ru",
    )
    session.idle_timeout_seconds = 0.01

    with pytest.raises(VoiceIdleTimeout):
        await session._browser_receive_loop()


@pytest.mark.asyncio
async def test_voice_policy_end_sends_clean_session_end() -> None:
    websocket = _FakeVoiceWebSocket()
    session = VoiceSession(
        websocket,
        user_id="u",
        session_id="s",
        language="ru",
    )

    await session._end_by_policy("max_duration")

    assert websocket.messages[-1] == {
        "type": "session_end",
        "reason": "max_duration",
    }
    assert websocket.closed == (1000, "max_duration")



def test_voice_audio_policy_accepts_normal_pcm_pacing() -> None:
    websocket = _FakeVoiceWebSocket()
    session = VoiceSession(
        websocket,
        user_id="u",
        session_id="s",
        language="ru",
    )
    session.max_frame_bytes = 65536
    session.audio_burst_seconds = 1.0
    session.max_audio_realtime_factor = 1.5

    assert session._audio_policy_violation(
        8192,
        now=100.0,
    ) is None
    assert session._audio_policy_violation(
        8192,
        now=100.25,
    ) is None


def test_voice_audio_policy_rejects_oversized_frame() -> None:
    websocket = _FakeVoiceWebSocket()
    session = VoiceSession(
        websocket,
        user_id="u",
        session_id="s",
        language="ru",
    )
    session.max_frame_bytes = 1024

    assert session._audio_policy_violation(
        1025,
        now=0.0,
    ) == "frame_too_large"


def test_voice_audio_policy_rejects_faster_than_realtime_flood() -> None:
    websocket = _FakeVoiceWebSocket()
    session = VoiceSession(
        websocket,
        user_id="u",
        session_id="s",
        language="ru",
    )
    session.max_frame_bytes = 65536
    session.audio_burst_seconds = 0.1
    session.max_audio_realtime_factor = 1.0

    assert session._audio_policy_violation(
        4000,
        now=0.0,
    ) == "audio_rate_limit"


@pytest.mark.asyncio
async def test_voice_policy_end_supports_policy_close_code() -> None:
    websocket = _FakeVoiceWebSocket()
    session = VoiceSession(
        websocket,
        user_id="u",
        session_id="s",
        language="ru",
    )

    await session._end_by_policy(
        "audio_rate_limit",
        code=1008,
    )

    assert websocket.messages[-1] == {
        "type": "session_end",
        "reason": "audio_rate_limit",
    }
    assert websocket.closed == (1008, "audio_rate_limit")



@pytest.mark.asyncio
async def test_successful_voice_turn_uses_one_turn_id_end_to_end(
    monkeypatch,
) -> None:
    captured_request_ids: list[str] = []

    class _FakeOrchestrator:
        async def handle_chat(self, request):
            captured_request_ids.append(request.request_id or "")
            return ChatResponse(
                reply="Ответ",
                request_id=request.request_id,
                user_id=request.user_id or "u",
                session_id=request.session_id or "s",
                intent="casual_conversation",
                avatar_state="soft_smile",
                provider="mock",
            )

    class _FakeTTSRouter:
        async def synthesize(self, text: str, *, language: str):
            return b"mp3", "fake-tts"

    monkeypatch.setattr(
        "telepat.voice.session.orchestrator",
        _FakeOrchestrator(),
    )
    monkeypatch.setattr(
        "telepat.voice.session.tts_router",
        _FakeTTSRouter(),
    )

    websocket = _FakeVoiceWebSocket()
    session = VoiceSession(
        websocket,
        user_id="u",
        session_id="s",
        language="ru",
    )
    session._active_turn_id = 4

    await session._respond(
        "Привет",
        turn_language="ru",
        turn_id=4,
    )

    turn_messages = [
        message
        for message in websocket.messages
        if message.get("type") in {
            "transcript",
            "state",
            "reply",
            "audio_start",
            "audio_end",
        }
    ]

    assert [message["type"] for message in turn_messages] == [
        "transcript",
        "state",
        "reply",
        "audio_start",
        "audio_end",
    ]
    assert all(
        message.get("turn_id") == 4
        for message in turn_messages
    )
    assert websocket.binary == [b"mp3"]
    assert captured_request_ids == [
        f"voice-{session._connection_id}-4"
    ]
    assert session._playback_turn_id == 4



class _PreAcceptDisconnectWebSocket(_FakeVoiceWebSocket):
    async def accept(self) -> None:
        raise RuntimeError(
            'Expected ASGI message "websocket.connect", '
            "but got 'websocket.disconnect'"
        )


@pytest.mark.asyncio
async def test_voice_pre_accept_disconnect_is_clean() -> None:
    websocket = _PreAcceptDisconnectWebSocket()
    session = VoiceSession(
        websocket,
        user_id="u",
        session_id="s",
        language="ru",
    )

    await session.run()

    assert websocket.messages == []
