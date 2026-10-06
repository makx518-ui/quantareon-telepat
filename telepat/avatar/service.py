from __future__ import annotations

from time import perf_counter

from telepat.observability.metrics import runtime_metrics

from .adapter import AvatarAdapter
from .models import AvatarRenderRequest, AvatarRenderResult


class AvatarService:
    """Runtime boundary between TELEPAT voice and a selected avatar engine."""

    def __init__(self, adapter: AvatarAdapter | None = None) -> None:
        self._adapter = adapter

    @property
    def configured(self) -> bool:
        return self._adapter is not None

    @property
    def engine(self) -> str | None:
        if self._adapter is None:
            return None
        return str(getattr(self._adapter, "name", "") or "") or None

    def set_adapter(self, adapter: AvatarAdapter | None) -> None:
        self._adapter = adapter

    async def render(
        self,
        *,
        audio: bytes,
        request: AvatarRenderRequest,
    ) -> AvatarRenderResult | None:
        adapter = self._adapter
        if adapter is None:
            return None
        if not audio:
            raise ValueError("avatar render audio must not be empty")

        started = perf_counter()
        engine = str(getattr(adapter, "name", "") or "").strip()
        if not engine:
            raise RuntimeError("avatar adapter name is required")

        try:
            data = await adapter.render(
                audio=audio,
                state=request.state,
            )
        except Exception:
            runtime_metrics.record(
                "avatar_render",
                (perf_counter() - started) * 1000,
                ok=False,
                provider=engine,
            )
            raise

        if not data:
            runtime_metrics.record(
                "avatar_render",
                (perf_counter() - started) * 1000,
                ok=False,
                provider=engine,
            )
            raise RuntimeError("avatar adapter returned empty media")

        latency_ms = (perf_counter() - started) * 1000
        runtime_metrics.record(
            "avatar_render",
            latency_ms,
            ok=True,
            provider=engine,
        )

        media_type = str(
            getattr(adapter, "media_type", "video/mp4")
            or "video/mp4"
        )

        return AvatarRenderResult(
            turn_id=request.turn_id,
            media_type=media_type,
            engine=engine,
            latency_ms=round(latency_ms, 2),
            data=bytes(data),
        )


avatar_service = AvatarService()
