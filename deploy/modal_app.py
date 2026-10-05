from __future__ import annotations

import modal


image = (
    modal.Image.debian_slim(python_version="3.12")
    .uv_pip_install(
        "fastapi>=0.115,<1",
        "pydantic>=2.8,<3",
        "httpx>=0.27,<1",
        "uvicorn[standard]>=0.30,<1",
        "kerykeion>=5.12,<6",
        "pyswisseph==2.10.3.2",
    )
    .add_local_python_source("telepat")
)

app = modal.App("quantareon-telepat", image=image)


@app.function()
@modal.asgi_app()
def web():
    from telepat.api.main import app as fastapi_app

    return fastapi_app
