from __future__ import annotations

import logging
from time import perf_counter

from telepat.observability.metrics import runtime_metrics

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
            started = perf_counter()
            try:
                audio = await yandex_tts.synthesize(
                    text,
                    language=language,
                )
                runtime_metrics.record(
                    "tts",
                    (perf_counter() - started) * 1000,
                    ok=True,
                    provider=yandex_tts.name,
                )
                return audio, yandex_tts.name
            except Exception as exc:
                runtime_metrics.record(
                    "tts",
                    (perf_counter() - started) * 1000,
                    ok=False,
                    provider=yandex_tts.name,
                )
                logger.warning(
                    "Yandex TTS failed, trying multilingual fallback: %s",
                    type(exc).__name__,
                )

        # Multilingual TELEPAT identity is Andrew. It is also the runtime
        # fallback for Russian when Ermil is temporarily unavailable.
        if microsoft_tts.configured:
            started = perf_counter()
            try:
                audio = await microsoft_tts.synthesize(
                    text,
                    language=language,
                )
                runtime_metrics.record(
                    "tts",
                    (perf_counter() - started) * 1000,
                    ok=True,
                    provider=microsoft_tts.name,
                )
                return audio, microsoft_tts.name
            except Exception as exc:
                runtime_metrics.record(
                    "tts",
                    (perf_counter() - started) * 1000,
                    ok=False,
                    provider=microsoft_tts.name,
                )
                logger.warning(
                    "Microsoft TTS failed: %s",
                    type(exc).__name__,
                )

        return None, None


tts_router = TTSRouter()
