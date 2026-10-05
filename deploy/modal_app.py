from __future__ import annotations

import modal

from deploy.runtime import app, cpu_image, provider_secrets


@app.function(
    image=cpu_image,
    secrets=provider_secrets,
    min_containers=0,
)
@modal.asgi_app()
def web():
    from telepat.api.main import app as fastapi_app

    return fastapi_app


# Import registers the GPU class on the same Modal App.
from deploy.avatar_gpu import AvatarGPUWorker  # noqa: E402,F401
