from __future__ import annotations

import math
from dataclasses import dataclass
from time import perf_counter
from typing import Callable

from .adapter import AvatarAdapter
from .states import AvatarState


def _percentile(values: list[float], fraction: float) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    index = max(
        0,
        min(
            len(ordered) - 1,
            int(round((len(ordered) - 1) * fraction)),
        ),
    )
    return ordered[index]


@dataclass(frozen=True, slots=True)
class AvatarBenchmarkSummary:
    engine: str
    runs: int
    warmup_ms: float
    p50_render_ms: float
    p95_render_ms: float
    max_render_ms: float
    real_time_factor_p50: float
    avg_output_bytes: int
    peak_vram_mb: float | None

    def as_dict(self) -> dict[str, object]:
        return {
            "engine": self.engine,
            "runs": self.runs,
            "warmup_ms": self.warmup_ms,
            "p50_render_ms": self.p50_render_ms,
            "p95_render_ms": self.p95_render_ms,
            "max_render_ms": self.max_render_ms,
            "real_time_factor_p50": self.real_time_factor_p50,
            "avg_output_bytes": self.avg_output_bytes,
            "peak_vram_mb": self.peak_vram_mb,
        }


async def benchmark_avatar_adapter(
    adapter: AvatarAdapter,
    *,
    audio: bytes,
    audio_duration_ms: float,
    state: AvatarState = "speaking",
    runs: int = 3,
    warmup_runs: int = 1,
    peak_vram_reader: Callable[[], float | None] | None = None,
) -> AvatarBenchmarkSummary:
    """Benchmark one avatar adapter with an identical audio payload.

    Identity/lip-sync visual quality remains a human comparison. This function
    measures only technical runtime characteristics.
    """
    if not audio:
        raise ValueError("audio must not be empty")
    if audio_duration_ms <= 0:
        raise ValueError("audio_duration_ms must be positive")
    if runs <= 0:
        raise ValueError("runs must be positive")
    if warmup_runs < 0:
        raise ValueError("warmup_runs must be non-negative")

    engine = str(getattr(adapter, "name", "") or "").strip()
    if not engine:
        raise ValueError("avatar adapter must expose a non-empty name")

    warmup_values: list[float] = []
    for _ in range(warmup_runs):
        started = perf_counter()
        await adapter.render(audio=audio, state=state)
        warmup_values.append((perf_counter() - started) * 1000)

    render_values: list[float] = []
    output_sizes: list[int] = []
    peak_vram: float | None = None

    for _ in range(runs):
        started = perf_counter()
        result = await adapter.render(audio=audio, state=state)
        elapsed_ms = (perf_counter() - started) * 1000

        render_values.append(elapsed_ms)
        output_sizes.append(len(result))

        if peak_vram_reader is not None:
            value = peak_vram_reader()
            if value is not None and math.isfinite(value):
                peak_vram = (
                    value
                    if peak_vram is None
                    else max(peak_vram, value)
                )

    p50 = _percentile(render_values, 0.50)

    return AvatarBenchmarkSummary(
        engine=engine,
        runs=runs,
        warmup_ms=round(
            sum(warmup_values) / len(warmup_values)
            if warmup_values
            else 0.0,
            2,
        ),
        p50_render_ms=round(p50, 2),
        p95_render_ms=round(_percentile(render_values, 0.95), 2),
        max_render_ms=round(max(render_values), 2),
        real_time_factor_p50=round(p50 / audio_duration_ms, 4),
        avg_output_bytes=round(sum(output_sizes) / len(output_sizes)),
        peak_vram_mb=(
            round(peak_vram, 2)
            if peak_vram is not None
            else None
        ),
    )
