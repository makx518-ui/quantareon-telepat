from __future__ import annotations

import asyncio

import pytest

from deploy.avatar_remote import (
    ModalAvatarAdapter,
    build_modal_avatar_adapter,
)


def test_remote_avatar_adapter_is_disabled_without_runtime_flags(
    monkeypatch,
) -> None:
    monkeypatch.delenv("TELEPAT_AVATAR_ENGINE", raising=False)
    monkeypatch.delenv("TELEPAT_AVATAR_GPU_ENABLED", raising=False)

    assert build_modal_avatar_adapter() is None


def test_remote_avatar_adapter_requires_gpu_enabled(
    monkeypatch,
) -> None:
    monkeypatch.setenv("TELEPAT_AVATAR_ENGINE", "musetalk-1.5")
    monkeypatch.setenv("TELEPAT_AVATAR_GPU_ENABLED", "0")

    assert build_modal_avatar_adapter() is None


@pytest.mark.asyncio
async def test_remote_avatar_adapter_preserves_contract() -> None:
    calls: list[tuple[bytes, str]] = []

    async def fake_render(audio: bytes, state: str) -> bytes:
        calls.append((audio, state))
        return b"video:" + audio

    adapter = ModalAvatarAdapter(
        engine="musetalk-1.5",
        render_callable=fake_render,
    )

    result = await adapter.render(
        audio=b"voice",
        state="speaking",
    )

    assert adapter.name == "musetalk-1.5"
    assert adapter.media_type == "video/mp4"
    assert result == b"video:voice"
    assert calls == [(b"voice", "speaking")]


def test_remote_avatar_adapter_builds_from_runtime_flags(
    monkeypatch,
) -> None:
    monkeypatch.setenv("TELEPAT_AVATAR_ENGINE", "latentsync-1.6")
    monkeypatch.setenv("TELEPAT_AVATAR_GPU_ENABLED", "1")
    monkeypatch.setenv(
        "TELEPAT_AVATAR_REMOTE_APP",
        "avatar-app",
    )
    monkeypatch.setenv(
        "TELEPAT_AVATAR_REMOTE_CLASS",
        "Worker",
    )

    adapter = build_modal_avatar_adapter()

    assert adapter is not None
    assert adapter.name == "latentsync-1.6"
    assert adapter.app_name == "avatar-app"
    assert adapter.class_name == "Worker"
