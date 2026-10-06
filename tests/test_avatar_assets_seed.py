from pathlib import Path

import pytest

from deploy import seed_avatar_assets


def test_validate_source_accepts_nonempty_mp4(tmp_path: Path) -> None:
    path = tmp_path / "source.mp4"
    path.write_bytes(
        b"\x00\x00\x00\x18ftypmp42" + b"x" * 1_000_000
    )

    seed_avatar_assets._validate_source(path)


def test_validate_source_rejects_tiny_or_non_mp4(tmp_path: Path) -> None:
    tiny = tmp_path / "tiny.mp4"
    tiny.write_bytes(b"\x00\x00\x00\x18ftypmp42")
    with pytest.raises(RuntimeError, match="unexpectedly small"):
        seed_avatar_assets._validate_source(tiny)

    bad = tmp_path / "bad.mp4"
    bad.write_bytes(b"x" * 1_000_001)
    with pytest.raises(RuntimeError, match="not an MP4"):
        seed_avatar_assets._validate_source(bad)
