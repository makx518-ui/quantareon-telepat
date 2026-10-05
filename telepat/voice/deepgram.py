from __future__ import annotations

import asyncio
import inspect
import json
import logging
import os
from collections.abc import Awaitable, Callable
from urllib.parse import urlencode

import websockets


logger = logging.getLogger(__name__)

TranscriptCallback = Callable[[str], None | Awaitable[None]]
EventCallback = Callable[[], None | Awaitable[None]]


_DEEPGRAM_BASE_LANGUAGES = {
    "ar", "be", "bg", "bn", "bs", "ca", "cs", "da", "de", "el", "en",
    "es", "et", "fa", "fi", "fr", "gu", "he", "hi", "hr", "hu", "id",
    "it", "ja", "kn", "ko", "lt", "lv", "mk", "mr", "ms", "nl", "no",
    "pl", "pt", "ro", "ru", "sk", "sl", "sr", "sv", "ta", "te", "th",
    "tl", "tr", "uk", "ur", "vi", "zh",
}

_DEEPGRAM_REGIONAL_LANGUAGES = {
    "da-dk": "da-DK",
    "de-ch": "de-CH",
    "en-au": "en-AU",
    "en-gb": "en-GB",
    "en-in": "en-IN",
    "en-nz": "en-NZ",
    "en-us": "en-US",
    "es-419": "es-419",
    "fr-ca": "fr-CA",
    "gu-in": "gu-IN",
    "ko-kr": "ko-KR",
    "nl-be": "nl-BE",
    "pt-br": "pt-BR",
    "pt-pt": "pt-PT",
    "sv-se": "sv-SE",
    "th-th": "th-TH",
    "zh-cn": "zh-CN",
    "zh-hans": "zh-Hans",
    "zh-hant": "zh-Hant",
    "zh-hk": "zh-HK",
    "zh-tw": "zh-TW",
}


def normalize_deepgram_language(language: str | None) -> str:
    value = (language or "multi").strip().replace("_", "-")
    lowered = value.lower()

    if lowered in {"", "auto", "multi"}:
        return "multi"

    if lowered in _DEEPGRAM_REGIONAL_LANGUAGES:
        return _DEEPGRAM_REGIONAL_LANGUAGES[lowered]

    base = lowered.split("-", 1)[0]
    if base in _DEEPGRAM_BASE_LANGUAGES:
        return base

    # Unknown browser locales fall back to Nova-3 multilingual instead of
    # being silently misclassified as Russian.
    return "multi"


class DeepgramStreamingSTT:
    """Cleaned streaming STT donor from QUANTARION Platform."""

    WS_URL = "wss://api.deepgram.com/v1/listen"

    def __init__(
        self,
        *,
        language: str = "ru",
        on_transcript: TranscriptCallback | None = None,
        on_interim: TranscriptCallback | None = None,
        on_speech_start: EventCallback | None = None,
        on_disconnect: EventCallback | None = None,
    ) -> None:
        self.api_key = os.getenv("DEEPGRAM_API_KEY", "")
        self.language = normalize_deepgram_language(language)
        self.on_transcript = on_transcript
        self.on_interim = on_interim
        self.on_speech_start = on_speech_start
        self.on_disconnect = on_disconnect

        self._ws = None
        self._receive_task: asyncio.Task | None = None
        self._keepalive_task: asyncio.Task | None = None
        self._final_segments: list[str] = []
        self._connected = False
        self._closing = False

    @property
    def configured(self) -> bool:
        return bool(self.api_key)

    def _url(self) -> str:
        params = {
            "model": "nova-3",
            "language": self.language,
            "punctuate": "true",
            "smart_format": "true",
            "filler_words": "false",
            "encoding": "linear16",
            "sample_rate": "16000",
            "channels": "1",
            "endpointing": "300",
            "utterance_end_ms": "1000",
            "vad_events": "true",
            "interim_results": "true",
        }
        return f"{self.WS_URL}?{urlencode(params)}"

    async def connect(self) -> None:
        if not self.configured:
            raise RuntimeError("DEEPGRAM_API_KEY is not configured")

        headers = {"Authorization": f"Token {self.api_key}"}
        try:
            self._ws = await websockets.connect(
                self._url(),
                additional_headers=headers,
                ping_interval=20,
                ping_timeout=20,
            )
        except TypeError:
            # websockets 12-13 compatibility
            self._ws = await websockets.connect(
                self._url(),
                extra_headers=headers,
                ping_interval=20,
                ping_timeout=20,
            )

        self._connected = True
        self._closing = False
        self._receive_task = asyncio.create_task(self._receive_loop())
        self._keepalive_task = asyncio.create_task(self._keepalive_loop())

    async def send_audio(self, audio: bytes) -> None:
        if not self._connected or self._ws is None:
            return
        await self._ws.send(audio)

    async def finalize(self) -> None:
        if self._connected and self._ws is not None:
            await self._ws.send(json.dumps({"type": "Finalize"}))

    async def close(self) -> None:
        self._closing = True
        self._connected = False

        current = asyncio.current_task()
        tasks = [
            task
            for task in (self._keepalive_task, self._receive_task)
            if task is not None and task is not current
        ]
        for task in tasks:
            task.cancel()

        if self._ws is not None:
            try:
                await self._ws.send(json.dumps({"type": "CloseStream"}))
            except Exception:
                pass
            try:
                await self._ws.close()
            except Exception:
                pass

        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)

        self._keepalive_task = None
        self._receive_task = None
        self._ws = None
        self._final_segments.clear()

    async def _keepalive_loop(self) -> None:
        try:
            while self._connected and self._ws is not None:
                await asyncio.sleep(5)
                await self._ws.send(json.dumps({"type": "KeepAlive"}))
        except asyncio.CancelledError:
            return
        except Exception as exc:
            if not self._closing:
                logger.warning("Deepgram keepalive stopped: %s", type(exc).__name__)

    async def _receive_loop(self) -> None:
        try:
            async for message in self._ws:
                if isinstance(message, bytes):
                    message = message.decode("utf-8", errors="ignore")
                await self._handle_message(message)
        except asyncio.CancelledError:
            return
        except Exception as exc:
            if not self._closing:
                logger.warning("Deepgram receive stopped: %s", type(exc).__name__)
        finally:
            was_unexpected = not self._closing
            self._connected = False
            if was_unexpected:
                await self._call(self.on_disconnect)

    async def _handle_message(self, payload: str) -> None:
        try:
            event = json.loads(payload)
        except json.JSONDecodeError:
            return

        event_type = event.get("type")

        if event_type == "Error":
            description = (
                event.get("description")
                or event.get("message")
                or "Deepgram stream error"
            )
            raise RuntimeError(str(description))

        if event_type == "SpeechStarted":
            # A fresh speech event must not inherit an unfinished stale buffer.
            self._final_segments.clear()
            await self._call(self.on_speech_start)
            return

        if event_type == "UtteranceEnd":
            await self._flush_final_segments()
            return

        if event_type != "Results":
            return

        alternatives = ((event.get("channel") or {}).get("alternatives") or [])
        if not alternatives:
            return

        best = alternatives[0]
        transcript = str(best.get("transcript") or "").strip()
        confidence = float(best.get("confidence") or 0)
        is_final = bool(event.get("is_final"))
        speech_final = bool(event.get("speech_final"))

        if transcript and not is_final:
            preview = " ".join(
                [*self._final_segments, transcript]
            ).strip()
            await self._call(self.on_interim, preview)
            return

        if transcript and is_final and confidence >= 0.50:
            self._final_segments.append(transcript)

        if speech_final:
            await self._flush_final_segments()

    async def _flush_final_segments(self) -> None:
        if not self._final_segments:
            return

        transcript = " ".join(self._final_segments).strip()
        self._final_segments.clear()

        if transcript:
            await self._call(self.on_transcript, transcript)

    @staticmethod
    async def _call(callback, *args) -> None:
        if callback is None:
            return
        result = callback(*args)
        if inspect.isawaitable(result):
            await result
