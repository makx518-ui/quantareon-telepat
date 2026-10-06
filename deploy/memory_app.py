from __future__ import annotations

import os

import modal

app = modal.App("quantareon-telepat-memory")
memory_volume = modal.Volume.from_name(
    "quantareon-telepat-memory",
    create_if_missing=True,
)
memory_secret = modal.Secret.from_name(
    "quantareon-telepat-memory-secrets"
)

memory_image = (
    modal.Image.debian_slim(python_version="3.12")
    .uv_pip_install(
        "fastapi>=0.115,<1",
        "pydantic>=2.8,<3",
    )
    .add_local_python_source("telepat", ignore=[])
)


@app.function(
    image=memory_image,
    secrets=[memory_secret],
    volumes={"/memory-data": memory_volume},
    memory=1024,
    timeout=300,
    max_containers=1,
    scaledown_window=120,
)
@modal.asgi_app()
def web():
    from telepat.memory_api.api import create_memory_app
    from telepat.memory_api.store import SQLiteMemoryStore

    store = SQLiteMemoryStore(
        "/memory-data/telepat-memory.sqlite3",
        max_exchanges_per_user=int(
            os.getenv(
                "TELEPAT_MEMORY_MAX_EXCHANGES_PER_USER",
                "240",
            )
        ),
        commit_callback=memory_volume.commit,
    )
    return create_memory_app(
        store=store,
        api_key=os.getenv("MEMORY_API_KEY", ""),
    )
