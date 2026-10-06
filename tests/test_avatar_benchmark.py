import asyncio

import pytest

from telepat.avatar.benchmark import benchmark_avatar_adapter


class _FakeAvatar:
    name = "fake-avatar"

    def __init__(self) -> None:
        self.calls = 0

    async def render(self, *, audio: bytes, state: str = "speaking") -> bytes:
        self.calls += 1
        await asyncio.sleep(0)
        return b"video-" + audio[:4]


@pytest.mark.asyncio
async def test_avatar_benchmark_reports_common_runtime_metrics() -> None:
    adapter = _FakeAvatar()
    vram = iter([1000.0, 1200.0, 1100.0])

    summary = await benchmark_avatar_adapter(
        adapter,
        audio=b"abcdef",
        audio_duration_ms=1000,
        runs=3,
        warmup_runs=1,
        peak_vram_reader=lambda: next(vram),
    )

    assert summary.engine == "fake-avatar"
    assert summary.runs == 3
    assert summary.p50_render_ms >= 0
    assert summary.p95_render_ms >= summary.p50_render_ms
    assert summary.real_time_factor_p50 >= 0
    assert summary.avg_output_bytes == len(b"video-abcd")
    assert summary.peak_vram_mb == 1200.0
    assert adapter.calls == 4


@pytest.mark.asyncio
async def test_avatar_benchmark_rejects_empty_audio() -> None:
    with pytest.raises(ValueError, match="audio"):
        await benchmark_avatar_adapter(
            _FakeAvatar(),
            audio=b"",
            audio_duration_ms=1000,
        )
