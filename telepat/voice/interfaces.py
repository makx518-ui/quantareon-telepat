from __future__ import annotations

from typing import Protocol, runtime_checkable


@runtime_checkable
class StreamingSTTProvider(Protocol):
    @property
    def configured(self) -> bool: ...

    async def connect(self) -> None: ...

    async def send_audio(self, audio: bytes) -> None: ...

    async def finalize(self) -> None: ...

    async def close(self) -> None: ...


@runtime_checkable
class TTSProvider(Protocol):
    name: str

    @property
    def configured(self) -> bool: ...

    async def synthesize(
        self,
        text: str,
        *,
        language: str,
    ) -> bytes: ...
