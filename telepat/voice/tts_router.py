from __future__ import annotations

from .microsoft_tts import microsoft_tts
from .yandex_tts import yandex_tts


class TTSRouter:
    async def synthesize(
        self,
        text: str,
        *,
        language: str,
    ) -> tuple[bytes, str] | tuple[None, None]:
        # Russian TELEPAT identity is Ermil.
        if language.lower().startswith("ru") and yandex_tts.configured:
            audio = await yandex_tts.synthesize(text, language=language)
            return audio, yandex_tts.name

        # Multilingual TELEPAT identity is Andrew when Azure is configured.
        if microsoft_tts.configured:
            audio = await microsoft_tts.synthesize(
                text,
                language=language,
            )
            return audio, microsoft_tts.name

        return None, None


tts_router = TTSRouter()
