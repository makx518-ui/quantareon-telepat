from __future__ import annotations

import json
import subprocess
from pathlib import Path

import modal

from deploy.runtime import assets_volume, provider_secrets
from telepat.avatar.assets import (
    avatar_asset_status,
    benchmark_audio_path,
)
from telepat.avatar.benchmark import benchmark_avatar_adapter
from telepat.avatar.gpu_probe import gpu_status


LATENTSYNC_COMMIT = "a229c3948406bc2cf6eaf4873e662e70c6a04746"

app = modal.App("quantareon-telepat-avatar-latentsync")

latentsync_image = (
    modal.Image.from_registry(
        "nvidia/cuda:12.1.1-cudnn8-runtime-ubuntu22.04",
        add_python="3.10",
    )
    .apt_install(
        "git",
        "ffmpeg",
        "libgl1",
        "libglib2.0-0",
        "build-essential",
    )
    .run_commands(
        "git clone https://github.com/bytedance/LatentSync.git /opt/LatentSync",
        f"cd /opt/LatentSync && git checkout {LATENTSYNC_COMMIT}",
        "pip install -r /opt/LatentSync/requirements.txt",
        (
            "cd /opt/LatentSync && "
            "huggingface-cli download ByteDance/LatentSync-1.6 "
            "whisper/tiny.pt latentsync_unet.pt "
            "--local-dir checkpoints"
        ),
        (
            "python -c \"from diffusers import AutoencoderKL; "
            "AutoencoderKL.from_pretrained('stabilityai/sd-vae-ft-mse')\""
        ),
    )
    .add_local_python_source("telepat", ignore=[])
    .add_local_python_source("deploy", ignore=[])
)


def _audio_duration_ms(path: Path) -> float:
    completed = subprocess.run(
        [
            "ffprobe",
            "-v",
            "error",
            "-show_entries",
            "format=duration",
            "-of",
            "default=noprint_wrappers=1:nokey=1",
            str(path),
        ],
        capture_output=True,
        text=True,
        timeout=20,
        check=True,
    )
    duration = float(completed.stdout.strip())
    if duration <= 0:
        raise RuntimeError("Benchmark audio duration is invalid")
    return duration * 1000.0


def _used_vram_mb() -> float | None:
    status = gpu_status()
    total = status.get("memory_total_mb")
    free = status.get("memory_free_mb")
    if not isinstance(total, (int, float)):
        return None
    if not isinstance(free, (int, float)):
        return None
    return max(0.0, float(total) - float(free))


@app.cls(
    image=latentsync_image,
    secrets=provider_secrets,
    gpu="L4",
    memory=24576,
    timeout=1200,
    scaledown_window=60,
    volumes={"/telepat-assets": assets_volume},
)
class LatentSyncBenchmarkWorker:
    @modal.method()
    async def benchmark(
        self,
        runs: int = 3,
        warmup_runs: int = 1,
    ) -> dict[str, object]:
        assets = avatar_asset_status()
        hardware = gpu_status()
        if not hardware.get("available"):
            raise RuntimeError("L4 GPU is not available")
        if not assets.get("ready"):
            raise RuntimeError(
                "Avatar benchmark assets are not ready: "
                + json.dumps(assets.get("missing") or [])
            )

        from telepat.avatar.latentsync import LatentSync16Adapter

        audio_path = benchmark_audio_path()
        audio = audio_path.read_bytes()
        adapter = LatentSync16Adapter()
        summary = await benchmark_avatar_adapter(
            adapter,
            audio=audio,
            audio_duration_ms=_audio_duration_ms(audio_path),
            runs=int(runs),
            warmup_runs=int(warmup_runs),
            peak_vram_reader=_used_vram_mb,
        )
        return {
            "ok": True,
            "hardware": hardware,
            "assets": assets,
            "benchmark": summary.as_dict(),
        }
