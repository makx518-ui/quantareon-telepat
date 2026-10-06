from __future__ import annotations

import os
from pathlib import Path
from typing import Any


def asset_root() -> Path:
    return Path(
        os.getenv("TELEPAT_AVATAR_ASSET_ROOT", "/telepat-assets")
    )


def source_video_path(root: Path | None = None) -> Path:
    base = root or asset_root()
    relative = os.getenv(
        "TELEPAT_AVATAR_SOURCE",
        "benchmark/source.mp4",
    )
    return base / relative


def benchmark_audio_path(root: Path | None = None) -> Path:
    base = root or asset_root()
    relative = os.getenv(
        "TELEPAT_AVATAR_AUDIO_SAMPLE",
        "benchmark/ermil-benchmark.mp3",
    )
    return base / relative


def avatar_asset_status(
    *,
    root: Path | None = None,
) -> dict[str, Any]:
    base = root or asset_root()
    source = source_video_path(base)
    audio = benchmark_audio_path(base)

    def describe(path: Path) -> dict[str, object]:
        exists = path.is_file()
        size = path.stat().st_size if exists else 0
        return {
            "path": str(path),
            "exists": exists,
            "non_empty": bool(size > 0),
            "bytes": size,
        }

    source_info = describe(source)
    audio_info = describe(audio)

    missing = []
    if not source_info["non_empty"]:
        missing.append("source_video")
    if not audio_info["non_empty"]:
        missing.append("benchmark_audio")

    return {
        "ready": not missing,
        "root": str(base),
        "source_video": source_info,
        "benchmark_audio": audio_info,
        "missing": missing,
    }
