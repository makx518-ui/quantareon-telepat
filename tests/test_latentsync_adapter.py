import pytest

from telepat.avatar.latentsync import LatentSync16Adapter


class _FakeRuntime:
    def __init__(self) -> None:
        self.calls: list[tuple[bytes, str]] = []

    def render_sync(
        self,
        *,
        audio: bytes,
        state: str = "speaking",
    ) -> bytes:
        self.calls.append((audio, state))
        return b"mp4:" + audio


@pytest.mark.asyncio
async def test_latentsync_adapter_implements_avatar_contract() -> None:
    runtime = _FakeRuntime()
    adapter = LatentSync16Adapter(runtime=runtime)

    result = await adapter.render(
        audio=b"voice",
        state="speaking",
    )

    assert adapter.name == "latentsync-1.6"
    assert adapter.media_type == "video/mp4"
    assert result == b"mp4:voice"
    assert runtime.calls == [(b"voice", "speaking")]
