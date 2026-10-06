from pathlib import Path

import pytest

from deploy.avatar_musetalk_benchmark import _audio_duration_ms


def test_musetalk_benchmark_duration_rejects_bad_probe(
    monkeypatch,
    tmp_path: Path,
) -> None:
    class _Completed:
        stdout = "0\n"

    monkeypatch.setattr(
        "deploy.avatar_musetalk_benchmark.subprocess.run",
        lambda *args, **kwargs: _Completed(),
    )

    with pytest.raises(RuntimeError, match="duration"):
        _audio_duration_ms(tmp_path / "audio.mp3")
