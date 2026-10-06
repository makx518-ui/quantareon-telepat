from __future__ import annotations

import asyncio
import inspect
import os
from collections.abc import Awaitable, Callable

import modal

from telepat.avatar.states import AvatarState


RenderCallable = Callable[
    [bytes, AvatarState],
    bytes | Awaitable[bytes],
]


class ModalAvatarAdapter:
    """CPU-side adapter for a separately deployed Modal GPU avatar worker."""

    media_type = "video/mp4"

    def __init__(
        self,
        *,
        engine: str,
        app_name: str = "quantareon-telepat-avatar",
        class_name: str = "AvatarGPUWorker",
        method_name: str = "render",
        render_callable: RenderCallable | None = None,
    ) -> None:
        name = str(engine or "").strip()
        if not name:
            raise ValueError("avatar engine is required")
        self.name = name
        self.app_name = app_name
        self.class_name = class_name
        self.method_name = method_name
        self._render_callable = render_callable

    def _remote_render(
        self,
        audio: bytes,
        state: AvatarState,
    ) -> bytes:
        avatar_cls = modal.Cls.from_name(
            self.app_name,
            self.class_name,
        )
        worker = avatar_cls()
        method = getattr(worker, self.method_name)
        result = method.remote(
            audio=audio,
            state=state,
        )
        if not isinstance(result, bytes) or not result:
            raise RuntimeError(
                "Remote avatar worker returned no binary media"
            )
        return result

    async def render(
        self,
        *,
        audio: bytes,
        state: AvatarState = "speaking",
    ) -> bytes:
        if not audio:
            raise ValueError("avatar render audio must not be empty")

        if self._render_callable is None:
            return await asyncio.to_thread(
                self._remote_render,
                audio,
                state,
            )

        result = self._render_callable(audio, state)
        if inspect.isawaitable(result):
            result = await result
        if not isinstance(result, bytes) or not result:
            raise RuntimeError(
                "Remote avatar worker returned no binary media"
            )
        return result


def build_modal_avatar_adapter() -> ModalAvatarAdapter | None:
    enabled = os.getenv(
        "TELEPAT_AVATAR_GPU_ENABLED",
        "0",
    ).strip().lower() in {"1", "true", "yes", "on"}
    engine = os.getenv("TELEPAT_AVATAR_ENGINE", "").strip()
    if not enabled or not engine:
        return None

    return ModalAvatarAdapter(
        engine=engine,
        app_name=os.getenv(
            "TELEPAT_AVATAR_REMOTE_APP",
            "quantareon-telepat-avatar",
        ).strip(),
        class_name=os.getenv(
            "TELEPAT_AVATAR_REMOTE_CLASS",
            "AvatarGPUWorker",
        ).strip(),
        method_name=os.getenv(
            "TELEPAT_AVATAR_REMOTE_METHOD",
            "render",
        ).strip(),
    )
