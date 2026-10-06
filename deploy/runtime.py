from __future__ import annotations

import os

import modal


# The named Secret is always attached. Deployment automation guarantees that
# the container exists (at minimum with a harmless management marker) before
# Modal hydrates functions. Keeping dependencies unconditional is required by
# Modal's object graph/hydration model.
telepat_secret = modal.Secret.from_name("quantareon-telepat-secrets")
provider_secrets = [telepat_secret]

app = modal.App("quantareon-telepat")

build_sha = os.getenv("TELEPAT_BUILD_SHA", "local").strip() or "local"

GOOGLE_GENAI_SPEC = "google-genai>=2.0,<3"

assets_volume = modal.Volume.from_name(
    "quantareon-telepat-assets",
    create_if_missing=True,
)

cpu_image = (
    modal.Image.debian_slim(python_version="3.12")
    .env({"TELEPAT_BUILD_SHA": build_sha})
    .uv_pip_install(
        "fastapi>=0.115,<1",
        "pydantic>=2.8,<3",
        "httpx>=0.27,<1",
        "uvicorn[standard]>=0.30,<1",
        GOOGLE_GENAI_SPEC,
        "websockets>=12,<16",
        "kerykeion>=5.12,<6",
        "pyswisseph==2.10.3.2",
    )
    .add_local_python_source("telepat", ignore=[])
    .add_local_python_source("deploy", ignore=[])
)

# Deliberately minimal until the lip-sync benchmark chooses the engine.
# We allocate an L4 only when a GPU method is actually called.
gpu_base_image = (
    modal.Image.debian_slim(python_version="3.12")
    .add_local_python_source("telepat", ignore=[])
    .add_local_python_source("deploy", ignore=[])
)
