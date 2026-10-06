from __future__ import annotations

import shutil
import tempfile
import urllib.request
from pathlib import Path

import modal


APP_NAME = "quantareon-telepat"
AUDIO_FUNCTION = "avatar_benchmark_audio"
VOLUME_NAME = "quantareon-telepat-assets"
SOURCE_URL = (
    "https://raw.githubusercontent.com/"
    "makx518-ui/quantareon-site/main/telepat-video-ru.mp4"
)
SOURCE_REMOTE = "/benchmark/source.mp4"
AUDIO_REMOTE = "/benchmark/ermil-benchmark.mp3"


def _download(url: str, target: Path) -> None:
    request = urllib.request.Request(
        url,
        headers={"User-Agent": "TELEPAT-avatar-asset-seed/1"},
    )
    with urllib.request.urlopen(request, timeout=90) as response:
        with target.open("wb") as output:
            shutil.copyfileobj(response, output)


def _validate_source(path: Path) -> None:
    if path.stat().st_size < 1_000_000:
        raise RuntimeError("TELEPAT source video is unexpectedly small")
    with path.open("rb") as fh:
        header = fh.read(64)
    if b"ftyp" not in header:
        raise RuntimeError("TELEPAT source video is not an MP4 container")


def _generate_audio(target: Path) -> None:
    function = modal.Function.from_name(APP_NAME, AUDIO_FUNCTION)
    audio = function.remote()
    if not isinstance(audio, bytes) or len(audio) < 1_000:
        raise RuntimeError("TELEPAT benchmark MP3 is unexpectedly small")
    target.write_bytes(audio)


def main() -> None:
    with tempfile.TemporaryDirectory(prefix="telepat-avatar-assets-") as tmp:
        root = Path(tmp)
        source = root / "source.mp4"
        audio = root / "ermil-benchmark.mp3"

        _download(SOURCE_URL, source)
        _validate_source(source)
        _generate_audio(audio)

        volume = modal.Volume.from_name(
            VOLUME_NAME,
            create_if_missing=True,
        )
        with volume.batch_upload(force=True) as batch:
            batch.put_file(source, SOURCE_REMOTE)
            batch.put_file(audio, AUDIO_REMOTE)

        print(
            "Seeded TELEPAT avatar benchmark assets: "
            f"source={source.stat().st_size} bytes, "
            f"audio={audio.stat().st_size} bytes."
        )


if __name__ == "__main__":
    main()
