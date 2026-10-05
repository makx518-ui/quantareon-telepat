from __future__ import annotations

import logging

from .microsoft_tts import microsoft_tts
from .yandex_tts import yandex_tts


logger = logging.getLogger(__name__)


class TTSRouter:
    async def synthesize(
        self,
        text: str,
        *,
        language: str,
    ) -> tuple[bytes, str] | tuple[None, None]:
        # Russian TELEPAT identity is Ermil.
        if language.lower().startswith("ru") and yandex_tts.configured:
            try:
                audio = await yandex_tts.synthesize(
                    text,
                    language=language,
                )
                return audio, yandex_tts.name
            except Exception as exc:
                logger.warning(
                    "Yandex TTS failed, trying multilingual fallback: %s",
                    type(exc).__name__,
                )

        # Multilingual TELEPAT identity is Andrew. It is also the runtime
        # fallback for Russian when Ermil is temporarily unavailable.
        if microsoft_tts.configured:
            try:
                audio = await microsoft_tts.synthesize(
                    text,
                    language=language,
                )
                return audio, microsoft_tts.name
            except Exception as exc:
                logger.warning(
                    "Microsoft TTS failed: %s",
                    type(exc).__name__,
                )

        return None, None


tts_router = TTSRouter()
