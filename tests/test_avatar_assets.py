from pathlib import Path

from telepat.avatar.assets import avatar_asset_status


def test_avatar_asset_status_reports_missing_files(tmp_path: Path) -> None:
    status = avatar_asset_status(root=tmp_path)

    assert status["ready"] is False
    assert status["missing"] == [
        "source_video",
        "benchmark_audio",
    ]


def test_avatar_asset_status_accepts_non_empty_benchmark_assets(
    tmp_path: Path,
) -> None:
    benchmark = tmp_path / "benchmark"
    benchmark.mkdir()

    (benchmark / "source.mp4").write_bytes(b"video")
    (benchmark / "ermil-benchmark.mp3").write_bytes(b"audio")

    status = avatar_asset_status(root=tmp_path)

    assert status["ready"] is True
    assert status["missing"] == []
    assert status["source_video"]["bytes"] == 5
    assert status["benchmark_audio"]["bytes"] == 5
