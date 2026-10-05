from __future__ import annotations

import modal

from deploy.runtime import app, assets_volume, gpu_base_image


@app.cls(
    image=gpu_base_image,
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
        return {
            "ok": True,
            "worker": "avatar-gpu",
            "gpu": "L4",
            "engine": None,
            "engine_selected": False,
            "assets_mount": "/telepat-assets",
        }
