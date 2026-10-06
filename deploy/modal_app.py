from __future__ import annotations

import os

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


# GPU registration is intentionally opt-in. Modal accounts without GPU billing
# must still be able to deploy and test the complete CPU/voice orchestration API.
register_gpu = os.getenv(
    "TELEPAT_REGISTER_GPU",
    "0",
).strip().lower() in {"1", "true", "yes", "on"}

if register_gpu:
    from deploy.avatar_gpu import AvatarGPUWorker  # noqa: E402,F401
