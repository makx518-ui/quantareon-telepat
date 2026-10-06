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


MUSE_TALK_COMMIT = "0a89dec45a0192b824e3cf4daf96c239440c5ed8"

app = modal.App("quantareon-telepat-avatar-musetalk")

musetalk_image = (
    modal.Image.from_registry(
        "nvidia/cuda:11.8.0-cudnn8-runtime-ubuntu22.04",
        add_python="3.10",
    )
    .apt_install(
        "git",
        "ffmpeg",
        "libgl1",
        "libglib2.0-0",
        "build-essential",
        "curl",
    )
    .run_commands(
        "git clone https://github.com/TMElyralab/MuseTalk.git /opt/MuseTalk",
        f"cd /opt/MuseTalk && git checkout {MUSE_TALK_COMMIT}",
        "pip install --upgrade pip setuptools wheel",
        (
            "pip install torch==2.0.1 torchvision==0.15.2 "
            "torchaudio==2.0.2 "
            "--extra-index-url https://download.pytorch.org/whl/cu118"
        ),
        "pip install -r /opt/MuseTalk/requirements.txt",
        "pip install -U openmim",
        'mim install "mmengine"',
        'mim install "mmcv==2.0.1"',
        'mim install "mmdet==3.1.0"',
        "pip install --no-build-isolation chumpy==0.70",
        'mim install "mmpose==1.1.0"',
        "pip install 'huggingface_hub[cli]==0.30.2' gdown",
        (
            "cd /opt/MuseTalk && "
            "mkdir -p models/musetalkV15 models/syncnet models/dwpose "
            "models/face-parse-bisent models/sd-vae models/whisper && "
            "huggingface-cli download TMElyralab/MuseTalk "
            "--local-dir models "
            "--include 'musetalkV15/musetalk.json' "
            "'musetalkV15/unet.pth' && "
            "huggingface-cli download stabilityai/sd-vae-ft-mse "
            "--local-dir models/sd-vae "
            "--include 'config.json' 'diffusion_pytorch_model.bin' && "
            "huggingface-cli download openai/whisper-tiny "
            "--local-dir models/whisper "
            "--include 'config.json' 'pytorch_model.bin' "
            "'preprocessor_config.json' && "
            "huggingface-cli download yzd-v/DWPose "
            "--local-dir models/dwpose "
            "--include 'dw-ll_ucoco_384.pth' && "
            "huggingface-cli download ByteDance/LatentSync "
            "--local-dir models/syncnet "
            "--include 'latentsync_syncnet.pt' && "
            "gdown 'https://drive.google.com/uc?id=154JgKpzCPW82qINcVieuPH3fZ2e0P812' "
            "-O models/face-parse-bisent/79999_iter.pth && "
            "curl -L https://download.pytorch.org/models/resnet18-5c106cde.pth "
            "-o models/face-parse-bisent/resnet18-5c106cde.pth"
        ),
        (
            "pip install --force-reinstall --no-deps "
            "'huggingface_hub==0.30.2'"
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
    image=musetalk_image,
    secrets=provider_secrets,
    gpu="L4",
    memory=16384,
    timeout=900,
    scaledown_window=60,
    volumes={"/telepat-assets": assets_volume},
)
class MuseTalkBenchmarkWorker:
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

        from telepat.avatar.musetalk import MuseTalk15Adapter

        audio_path = benchmark_audio_path()
        audio = audio_path.read_bytes()
        adapter = MuseTalk15Adapter()
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
