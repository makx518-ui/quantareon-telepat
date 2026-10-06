from __future__ import annotations

import os
import subprocess
import tempfile
import urllib.request
from pathlib import Path

import modal

from telepat.avatar.gpu_probe import gpu_status


SKYREELS_COMMIT = "28c771e8456341be6a213e3d1133ed1fd19bf75d"
SKYREELS_REPO = "/opt/SkyReels-V3"
SKYREELS_DATA_ROOT = "/skyreels-data"
SKYREELS_MODEL_ID = "Skywork/SkyReels-V3-A2V-19B"
SKYREELS_MODEL_DIR = f"{SKYREELS_DATA_ROOT}/models/talking-avatar"

PUBLIC_IMAGE_URL = (
    "https://skyreels-api.oss-accelerate.aliyuncs.com/examples/"
    "talking_avatar_video/single1.png"
)
PUBLIC_AUDIO_URL = (
    "https://skyreels-api.oss-accelerate.aliyuncs.com/examples/"
    "talking_avatar_video/single_actor/huahai_5s.mp3"
)


app = modal.App("quantareon-telepat-video-skyreels")
skyreels_volume = modal.Volume.from_name(
    "quantareon-telepat-skyreels",
    create_if_missing=True,
)

skyreels_image = (
    modal.Image.from_registry(
        "nvidia/cuda:12.8.1-cudnn-devel-ubuntu22.04",
        add_python="3.12",
    )
    .apt_install(
        "git",
        "ffmpeg",
        "build-essential",
        "ninja-build",
        "libgl1",
        "libglib2.0-0",
        "libsndfile1",
        "curl",
    )
    .env(
        {
            "HF_HOME": f"{SKYREELS_DATA_ROOT}/hf",
            "PYTORCH_CUDA_ALLOC_CONF": "expandable_segments:True",
            "MAX_JOBS": "4",
        }
    )
    .run_commands(
        "git clone https://github.com/SkyworkAI/SkyReels-V3.git "
        f"{SKYREELS_REPO}",
        f"cd {SKYREELS_REPO} && git checkout {SKYREELS_COMMIT}",
        "python -m pip install --upgrade pip setuptools wheel ninja packaging",
        "pip install torch==2.8.0 torchvision==0.23.0",
        (
            f"grep -vE '^(torch==|torchvision==|flash_attn==)' "
            f"{SKYREELS_REPO}/requirements.txt > /tmp/skyreels-requirements.txt"
        ),
        "pip install -r /tmp/skyreels-requirements.txt",
        # SkyReels falls back to PyTorch SDPA when flash-attn is absent.
        # Avoid compiling flash-attn during Modal image build; it can take
        # tens of minutes and is not required for the first L40S validation.
    )
    .add_local_python_source("telepat", ignore=[])
    .add_local_python_source("deploy", ignore=[])
)


def _model_ready() -> bool:
    path = Path(SKYREELS_MODEL_DIR)
    return path.is_dir() and any(path.glob("*.safetensors"))


def _directory_stats(path: str) -> tuple[int, int]:
    root = Path(path)
    if not root.exists():
        return 0, 0
    count = 0
    total_bytes = 0
    for file in root.rglob("*"):
        if file.is_file():
            count += 1
            total_bytes += file.stat().st_size
    return count, total_bytes


@app.function(
    image=skyreels_image,
    memory=16384,
    timeout=7200,
    volumes={SKYREELS_DATA_ROOT: skyreels_volume},
)
def prepare_talking_avatar_model() -> dict[str, object]:
    from huggingface_hub import snapshot_download

    Path(SKYREELS_MODEL_DIR).mkdir(parents=True, exist_ok=True)
    resolved = snapshot_download(
        repo_id=SKYREELS_MODEL_ID,
        local_dir=SKYREELS_MODEL_DIR,
    )
    skyreels_volume.commit()
    file_count, total_bytes = _directory_stats(SKYREELS_MODEL_DIR)
    return {
        "ok": True,
        "model_id": SKYREELS_MODEL_ID,
        "model_dir": resolved,
        "file_count": file_count,
        "total_bytes": total_bytes,
        "total_gib": round(total_bytes / (1024**3), 2),
        "pinned_commit": SKYREELS_COMMIT,
    }


@app.cls(
    image=skyreels_image,
    gpu="L40S",
    memory=131072,
    timeout=7200,
    scaledown_window=120,
    volumes={SKYREELS_DATA_ROOT: skyreels_volume},
)
class SkyReelsV3Worker:
    @modal.method()
    def probe(self) -> dict[str, object]:
        hardware = gpu_status()
        file_count, total_bytes = _directory_stats(SKYREELS_MODEL_DIR)
        return {
            "ok": bool(hardware.get("available")),
            "worker": "skyreels-v3-talking-avatar",
            "requested_gpu": "L40S",
            "hardware": hardware,
            "model_id": SKYREELS_MODEL_ID,
            "model_ready": _model_ready(),
            "model_file_count": file_count,
            "model_gib": round(total_bytes / (1024**3), 2),
            "pinned_commit": SKYREELS_COMMIT,
            "capabilities": {
                "talking_avatar": True,
                "max_audio_seconds": 200,
                "native_resolution": "720P",
                "fps": 25,
            },
        }

    def _render(
        self,
        *,
        image_path: Path,
        audio_path: Path,
        prompt: str,
        resolution: str,
        seed: int,
        low_vram: bool,
    ) -> bytes:
        if not _model_ready():
            raise RuntimeError(
                "SkyReels V3 model weights are not prepared. "
                "Run prepare_talking_avatar_model first."
            )
        if resolution not in {"480P", "720P"}:
            raise ValueError("SkyReels talking avatar supports 480P or 720P")

        with tempfile.TemporaryDirectory(prefix="telepat-skyreels-") as tmp:
            workdir = Path(tmp)
            cmd = [
                "python",
                f"{SKYREELS_REPO}/generate_video.py",
                "--task_type",
                "talking_avatar",
                "--model_id",
                SKYREELS_MODEL_DIR,
                "--prompt",
                prompt,
                "--seed",
                str(int(seed)),
                "--offload",
                "--resolution",
                resolution,
                "--input_image",
                str(image_path),
                "--input_audio",
                str(audio_path),
            ]
            if low_vram:
                cmd.append("--low_vram")

            completed = subprocess.run(
                cmd,
                cwd=workdir,
                env=os.environ.copy(),
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                timeout=7000,
            )
            if completed.returncode != 0:
                tail = completed.stdout[-12000:]
                raise RuntimeError(
                    "SkyReels V3 render failed "
                    f"(exit={completed.returncode}):\n{tail}"
                )

            result_dir = workdir / "result" / "talking_avatar"
            candidates = sorted(
                result_dir.glob("*_with_audio.mp4"),
                key=lambda path: path.stat().st_mtime,
            )
            if not candidates:
                candidates = sorted(
                    result_dir.glob("*.mp4"),
                    key=lambda path: path.stat().st_mtime,
                )
            if not candidates:
                raise RuntimeError(
                    "SkyReels V3 completed but produced no MP4"
                )
            data = candidates[-1].read_bytes()
            if not data:
                raise RuntimeError("SkyReels V3 produced an empty MP4")
            return data

    @modal.method()
    def render_talking_avatar(
        self,
        image: bytes,
        audio: bytes,
        prompt: str = (
            "A charismatic man speaks calmly to the camera with subtle, "
            "natural facial expressions and restrained hand movement. "
            "Static cinematic shot."
        ),
        resolution: str = "720P",
        seed: int = 42,
        low_vram: bool = False,
    ) -> bytes:
        if not image:
            raise ValueError("image must not be empty")
        if not audio:
            raise ValueError("audio must not be empty")

        with tempfile.TemporaryDirectory(
            prefix="telepat-skyreels-input-"
        ) as tmp:
            root = Path(tmp)
            image_path = root / "input.png"
            audio_path = root / "input.mp3"
            image_path.write_bytes(image)
            audio_path.write_bytes(audio)
            return self._render(
                image_path=image_path,
                audio_path=audio_path,
                prompt=prompt,
                resolution=resolution,
                seed=seed,
                low_vram=low_vram,
            )

    @modal.method()
    def sample_public(
        self,
        duration_seconds: int = 5,
        resolution: str = "480P",
        low_vram: bool = False,
    ) -> bytes:
        duration_seconds = int(duration_seconds)
        if duration_seconds < 1 or duration_seconds > 200:
            raise ValueError("duration_seconds must be between 1 and 200")

        with tempfile.TemporaryDirectory(
            prefix="telepat-skyreels-public-"
        ) as tmp:
            root = Path(tmp)
            image_path = root / "sample.png"
            source_audio = root / "source.mp3"
            audio_path = root / "sample.mp3"
            urllib.request.urlretrieve(PUBLIC_IMAGE_URL, image_path)
            urllib.request.urlretrieve(PUBLIC_AUDIO_URL, source_audio)

            subprocess.run(
                [
                    "ffmpeg",
                    "-y",
                    "-stream_loop",
                    "-1",
                    "-i",
                    str(source_audio),
                    "-t",
                    str(duration_seconds),
                    "-c:a",
                    "libmp3lame",
                    "-q:a",
                    "3",
                    str(audio_path),
                ],
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                check=True,
                timeout=120,
            )
            return self._render(
                image_path=image_path,
                audio_path=audio_path,
                prompt=(
                    "A person speaks naturally to the camera with calm, "
                    "subtle expression and stable identity. Static shot."
                ),
                resolution=resolution,
                seed=42,
                low_vram=low_vram,
            )
