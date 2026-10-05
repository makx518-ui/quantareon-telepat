from __future__ import annotations

import asyncio
import json
import logging

from fastapi import WebSocket, WebSocketDisconnect

from telepat.core.models import ChatRequest
from telepat.core.orchestrator import orchestrator

from .deepgram import DeepgramStreamingSTT
from .tts_router import tts_router


logger = logging.getLogger(__name__)


class VoiceSession:
    """One browser voice connection.

    Current pipeline:
      browser PCM16 -> Deepgram -> Orchestrator -> TTS -> browser audio

    Avatar integration will replace only the final delivery stage:
      TTS -> Avatar GPU -> browser media
    """

    def __init__(
        self,
        websocket: WebSocket,
        *,
        user_id: str | None,
        session_id: str | None,
        language: str,
    ) -> None:
        self.websocket = websocket
        self.user_id = user_id
        self.session_id = session_id
        self.language = language or "ru"

        self._transcripts: asyncio.Queue[str] = asyncio.Queue(maxsize=20)
        self._processor_task: asyncio.Task | None = None
        self._response_task: asyncio.Task | None = None
        self._audio_playback_active = False
        self._closed = False

        self.stt = DeepgramStreamingSTT(
            language=self.language,
            on_transcript=self._on_transcript,
            on_interim=self._on_interim,
            on_speech_start=self._on_speech_start,
        )

    async def run(self) -> None:
        await self.websocket.accept()

        if not self.stt.configured:
            await self.websocket.send_json(
                {
                    "type": "error",
                    "stage": "stt",
                    "message": "Deepgram is not configured",
                }
            )
            await self.websocket.close(code=1011)
            return

        try:
            await self.stt.connect()
            self._processor_task = asyncio.create_task(
                self._process_transcripts()
            )
            await self.websocket.send_json(
                {
                    "type": "ready",
                    "sample_rate": 16000,
                    "encoding": "linear16",
                    "language": self.language,
                }
            )
            await self._browser_receive_loop()

        except WebSocketDisconnect:
            pass
        except Exception as exc:
            logger.exception("Voice session failed")
            try:
                await self.websocket.send_json(
                    {
                        "type": "error",
                        "stage": "session",
                        "message": type(exc).__name__,
                    }
                )
            except Exception:
                pass
        finally:
            await self.close()

    async def close(self) -> None:
        if self._closed:
            return
        self._closed = True

        if self._response_task and not self._response_task.done():
            self._response_task.cancel()
        if self._processor_task:
            self._processor_task.cancel()

        await self.stt.close()

        try:
            await self.websocket.close()
        except Exception:
            pass

    async def _browser_receive_loop(self) -> None:
        while not self._closed:
            event = await self.websocket.receive()
            kind = event.get("type")

            if kind == "websocket.disconnect":
                raise WebSocketDisconnect()

            audio = event.get("bytes")
            if audio:
                await self.stt.send_audio(audio)
                continue

            text = event.get("text")
            if text:
                await self._handle_control(text)

    async def _handle_control(self, text: str) -> None:
        try:
            message = json.loads(text)
        except json.JSONDecodeError:
            return

        kind = message.get("type")
        if kind == "finalize":
            await self.stt.finalize()
        elif kind == "ping":
            await self.websocket.send_json({"type": "pong"})
        elif kind == "playback_end":
            self._audio_playback_active = False

    async def _on_interim(self, transcript: str) -> None:
        try:
            await self.websocket.send_json(
                {
                    "type": "transcript",
                    "text": transcript,
                    "final": False,
                }
            )
        except Exception:
            pass

    async def _on_transcript(self, transcript: str) -> None:
        if self._transcripts.full():
            try:
                self._transcripts.get_nowait()
            except asyncio.QueueEmpty:
                pass
        self._transcripts.put_nowait(transcript)

    async def _on_speech_start(self) -> None:
        """Barge-in cancels generation and any browser-side playback."""
        response_active = (
            self._response_task is not None
            and not self._response_task.done()
        )
        if response_active:
            self._response_task.cancel()

        if response_active or self._audio_playback_active:
            self._audio_playback_active = False
            try:
                await self.websocket.send_json({"type": "barge_in"})
            except Exception:
                pass

    async def _process_transcripts(self) -> None:
        while not self._closed:
            transcript = await self._transcripts.get()

            if self._response_task and not self._response_task.done():
                self._response_task.cancel()

            self._response_task = asyncio.create_task(
                self._respond(transcript)
            )
            try:
                await self._response_task
            except asyncio.CancelledError:
                continue

    async def _respond(self, transcript: str) -> None:
        try:
            await self.websocket.send_json(
                {
                    "type": "transcript",
                    "text": transcript,
                    "final": True,
                }
            )
            await self.websocket.send_json(
                {
                    "type": "state",
                    "state": "thinking",
                }
            )

            response = await orchestrator.handle_chat(
                ChatRequest(
                    message=transcript,
                    user_id=self.user_id,
                    session_id=self.session_id,
                    language=self.language,
                )
            )
            self.user_id = response.user_id
            self.session_id = response.session_id

            await self.websocket.send_json(
                {
                    "type": "reply",
                    "text": response.reply,
                    "user_id": response.user_id,
                    "session_id": response.session_id,
                    "intent": response.intent,
                    "avatar_state": response.avatar_state,
                    "provider": response.provider,
                }
            )

            audio, tts_provider = await tts_router.synthesize(
                response.reply,
                language=self.language,
            )
            if not audio:
                await self.websocket.send_json(
                    {
                        "type": "audio_unavailable",
                        "reason": "tts_not_configured_or_failed",
                    }
                )
                return

            self._audio_playback_active = True
            await self.websocket.send_json(
                {
                    "type": "audio_start",
                    "format": "mp3",
                    "provider": tts_provider,
                    "avatar_state": response.avatar_state,
                }
            )
            await self.websocket.send_bytes(audio)
            await self.websocket.send_json({"type": "audio_end"})

        except asyncio.CancelledError:
            raise
        except Exception as exc:
            self._audio_playback_active = False
            logger.warning(
                "Voice response failed: %s",
                type(exc).__name__,
            )
            try:
                await self.websocket.send_json(
                    {
                        "type": "error",
                        "stage": "response",
                        "message": type(exc).__name__,
                    }
                )
            except Exception:
                pass
