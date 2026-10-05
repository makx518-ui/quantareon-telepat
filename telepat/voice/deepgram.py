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


class DeepgramStreamingSTT:
    """Cleaned streaming STT donor from QUANTARION Platform."""

    WS_URL = "wss://api.deepgram.com/v1/listen"

    def __init__(
        self,
        *,
        language: str = "ru",
        on_transcript: TranscriptCallback | None = None,
        on_speech_start: EventCallback | None = None,
    ) -> None:
        self.api_key = os.getenv("DEEPGRAM_API_KEY", "")
        self.language = "en" if language.lower().startswith("en") else "ru"
        self.on_transcript = on_transcript
        self.on_speech_start = on_speech_start

        self._ws = None
        self._receive_task: asyncio.Task | None = None
        self._keepalive_task: asyncio.Task | None = None
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

        for task in (self._keepalive_task, self._receive_task):
            if task:
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
            self._connected = False

    async def _handle_message(self, payload: str) -> None:
        try:
            event = json.loads(payload)
        except json.JSONDecodeError:
            return

        event_type = event.get("type")

        if event_type == "SpeechStarted":
            await self._call(self.on_speech_start)
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

        accepted = (
            transcript
            and (
                (is_final and confidence >= 0.70)
                or (speech_final and confidence >= 0.50)
            )
        )
        if accepted:
            await self._call(self.on_transcript, transcript)

    @staticmethod
    async def _call(callback, *args) -> None:
        if callback is None:
            return
        result = callback(*args)
        if inspect.isawaitable(result):
            await result
