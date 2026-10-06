from __future__ import annotations

import modal

from deploy.runtime import app, cpu_image, provider_secrets


@app.function(
    image=cpu_image,
    secrets=provider_secrets,
    min_containers=0,
    max_containers=1,
    scaledown_window=600,
)
@modal.asgi_app()
def web():
    from deploy.avatar_remote import build_modal_avatar_adapter
    from telepat.avatar.service import avatar_service

    avatar_service.set_adapter(build_modal_avatar_adapter())

    from telepat.api.main import app as fastapi_app

    return fastapi_app


@app.function(
    image=cpu_image,
    secrets=provider_secrets,
    timeout=240,
)
async def provider_probe() -> dict[str, object]:
    from telepat.diagnostics.provider_probe import run_provider_probe

    return await run_provider_probe()


@app.function(
    image=cpu_image,
    secrets=provider_secrets,
    timeout=60,
)
async def voice_smoke_audio() -> bytes:
    """Generate provider-backed PCM used only by the deploy voice smoke."""
    from telepat.voice.yandex_tts import yandex_tts

    audio = await yandex_tts.synthesize_lpcm(
        "Привет, Телепат. Скажи коротко, что ты меня слышишь.",
        language="ru",
        sample_rate_hertz=16000,
    )
    if not audio:
        raise RuntimeError("Yandex voice smoke audio is empty")
    return audio



@app.function(
    image=cpu_image,
    secrets=provider_secrets,
    timeout=60,
)
async def avatar_benchmark_audio() -> bytes:
    """Generate the fixed Ermil MP3 used by avatar engine benchmarks."""
    from telepat.voice.yandex_tts import yandex_tts

    audio = await yandex_tts.synthesize(
        (
            "Телепат готов к разговору. "
            "Я слышу тебя и отвечаю спокойно, точно и по существу."
        ),
        language="ru",
    )
    if not audio:
        raise RuntimeError("Yandex avatar benchmark audio is empty")
    return audio
