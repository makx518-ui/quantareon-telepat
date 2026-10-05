from __future__ import annotations

import modal


telepat_secret = modal.Secret.from_name("quantareon-telepat-secrets")

app = modal.App(
    "quantareon-telepat",
    secrets=[telepat_secret],
)

assets_volume = modal.Volume.from_name(
    "quantareon-telepat-assets",
    create_if_missing=True,
)

cpu_image = (
    modal.Image.debian_slim(python_version="3.12")
    .uv_pip_install(
        "fastapi>=0.115,<1",
        "pydantic>=2.8,<3",
        "httpx>=0.27,<1",
        "uvicorn[standard]>=0.30,<1",
        "google-genai>=1.0,<2",
        "websockets>=12,<16",
        "kerykeion>=5.12,<6",
        "pyswisseph==2.10.3.2",
    )
    .add_local_python_source("telepat", ignore=[])
)

# Deliberately minimal until the lip-sync benchmark chooses the engine.
# We allocate an L4 only when a GPU method is actually called.
gpu_base_image = modal.Image.debian_slim(python_version="3.12")
