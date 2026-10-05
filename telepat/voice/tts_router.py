from __future__ import annotations

from .yandex_tts import yandex_tts


class TTSRouter:
    async def synthesize(
        self,
        text: str,
        *,
        language: str,
    ) -> tuple[bytes, str] | tuple[None, None]:
        if language.lower().startswith("ru") and yandex_tts.configured:
            audio = await yandex_tts.synthesize(text, language=language)
            return audio, yandex_tts.name

        # Microsoft multilingual provider is added in the next voice phase.
        return None, None


tts_router = TTSRouter()
