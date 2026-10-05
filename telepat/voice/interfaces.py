from __future__ import annotations

from typing import AsyncIterator, Protocol


class STTProvider(Protocol):
    async def transcribe(self, audio: bytes, *, language: str | None = None) -> str: ...


class TTSProvider(Protocol):
    async def synthesize(self, text: str, *, language: str) -> bytes: ...

    async def stream(self, text: str, *, language: str) -> AsyncIterator[bytes]: ...
