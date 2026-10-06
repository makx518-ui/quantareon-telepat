import pytest

from telepat.avatar.models import AvatarRenderRequest
from telepat.avatar.service import AvatarService


class _FakeAvatar:
    name = "fake-avatar"
    media_type = "video/mp4"

    async def render(self, *, audio: bytes, state: str = "speaking") -> bytes:
        return b"video:" + audio


class _EmptyAvatar:
    name = "empty-avatar"

    async def render(self, *, audio: bytes, state: str = "speaking") -> bytes:
        return b""


@pytest.mark.asyncio
async def test_avatar_service_is_noop_without_adapter() -> None:
    service = AvatarService()

    result = await service.render(
        audio=b"audio",
        request=AvatarRenderRequest(
            turn_id=3,
            state="speaking",
        ),
    )

    assert service.configured is False
    assert service.engine is None
    assert result is None


@pytest.mark.asyncio
async def test_avatar_service_preserves_turn_and_engine_metadata() -> None:
    service = AvatarService(_FakeAvatar())

    result = await service.render(
        audio=b"audio",
        request=AvatarRenderRequest(
            turn_id=7,
            state="speaking",
            session_id="s",
            user_id="u",
        ),
    )

    assert result is not None
    assert result.turn_id == 7
    assert result.engine == "fake-avatar"
    assert result.media_type == "video/mp4"
    assert result.data == b"video:audio"
    assert result.latency_ms >= 0


@pytest.mark.asyncio
async def test_avatar_service_rejects_empty_media() -> None:
    service = AvatarService(_EmptyAvatar())

    with pytest.raises(RuntimeError, match="empty media"):
        await service.render(
            audio=b"audio",
            request=AvatarRenderRequest(
                turn_id=1,
                state="speaking",
            ),
        )
