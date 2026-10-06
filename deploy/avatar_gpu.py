from __future__ import annotations

import os

import modal

from deploy.runtime import assets_volume, gpu_base_image, provider_secrets
from telepat.avatar.assets import avatar_asset_status
from telepat.avatar.gpu_probe import gpu_status


avatar_app = modal.App("quantareon-telepat-avatar")
# Modal CLI discovers `app` by convention when deploying a module path.
app = avatar_app
# Modal CLI discovers a top-level `app` by convention.
app = avatar_app


@avatar_app.cls(
    image=gpu_base_image,
    secrets=provider_secrets,
    gpu="L4",
    memory=8192,
    timeout=300,
    scaledown_window=60,
    volumes={"/telepat-assets": assets_volume},
)
class AvatarGPUWorker:
    """GPU boundary for the future lip-sync engine.

    No fake renderer is installed here. The class exists now so CPU backend,
    persistent assets and GPU lifecycle are architecturally fixed before a
    specific avatar model is selected by benchmark.
    """

    @modal.method()
    def probe(self) -> dict[str, object]:
        engine = os.getenv("TELEPAT_AVATAR_ENGINE", "").strip()
        assets = avatar_asset_status()
        hardware = gpu_status()

        return {
            "ok": bool(hardware.get("available")),
            "worker": "avatar-gpu",
            "requested_gpu": "L4",
            "hardware": hardware,
            "engine": engine or None,
            "engine_selected": bool(engine),
            "assets_mount": "/telepat-assets",
            "assets": assets,
            "benchmark_ready": bool(
                hardware.get("available")
                and assets.get("ready")
                and engine
            ),
        }
