import pytest
from pydantic import ValidationError

from telepat.avatar.models import (
    AvatarRenderRequest,
    AvatarRenderResult,
)


def test_avatar_render_models_carry_voice_turn_id() -> None:
    request = AvatarRenderRequest(
        turn_id=7,
        state="speaking",
        session_id="s",
    )
    result = AvatarRenderResult(
        turn_id=7,
        media_type="video/mp4",
        engine="fake",
        latency_ms=12.5,
        data=b"video",
    )

    assert request.turn_id == 7
    assert result.turn_id == 7


@pytest.mark.parametrize("value", [0, -1])
def test_avatar_turn_id_must_be_positive(value: int) -> None:
    with pytest.raises(ValidationError):
        AvatarRenderRequest(
            turn_id=value,
            state="speaking",
        )
