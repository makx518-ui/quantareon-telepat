from __future__ import annotations

import asyncio
import os
import sys
import tempfile
import threading
from pathlib import Path
from types import SimpleNamespace
from uuid import uuid4

from .assets import source_video_path
from .states import AvatarState


class MuseTalkRuntimeUnavailable(RuntimeError):
    pass


class MuseTalk15Runtime:
    """Pinned MuseTalk 1.5 runtime behind TELEPAT's AvatarAdapter boundary."""

    name = "musetalk-1.5"
    media_type = "video/mp4"

    def __init__(
        self,
        *,
        repo_root: str | Path = "/opt/MuseTalk",
        cache_root: str | Path = "/telepat-assets/musetalk",
        source_video: str | Path | None = None,
        avatar_id: str = "telepat-benchmark",
        fps: int = 25,
        batch_size: int = 8,
    ) -> None:
        self.repo_root = Path(repo_root)
        self.cache_root = Path(cache_root)
        self.source_video = (
            Path(source_video) if source_video else source_video_path()
        )
        self.avatar_id = avatar_id
        self.fps = int(fps)
        self.batch_size = int(batch_size)
        self._module = None
        self._avatar = None
        self._render_lock = threading.Lock()

    @property
    def loaded(self) -> bool:
        return self._avatar is not None

    def load(self) -> None:
        if self.loaded:
            return
        if not self.repo_root.is_dir():
            raise MuseTalkRuntimeUnavailable(
                f"MuseTalk repository missing: {self.repo_root}"
            )
        if not self.source_video.is_file():
            raise MuseTalkRuntimeUnavailable(
                f"Avatar source video missing: {self.source_video}"
            )

        self.cache_root.mkdir(parents=True, exist_ok=True)
        persistent_results = self.cache_root / "results"
        persistent_results.mkdir(parents=True, exist_ok=True)
        repo_results = self.repo_root / "results"

        if repo_results.is_symlink():
            if repo_results.resolve() != persistent_results.resolve():
                repo_results.unlink()
        elif repo_results.exists():
            if any(repo_results.iterdir()):
                raise MuseTalkRuntimeUnavailable(
                    "MuseTalk image contains a non-empty results directory"
                )
            repo_results.rmdir()

        if not repo_results.exists():
            repo_results.symlink_to(
                persistent_results,
                target_is_directory=True,
            )

        repo_text = str(self.repo_root)
        if repo_text not in sys.path:
            sys.path.insert(0, repo_text)

        previous_cwd = Path.cwd()
        try:
            os.chdir(self.repo_root)
            import importlib
            import torch

            runtime = importlib.import_module(
                "scripts.realtime_inference"
            )
            args = SimpleNamespace(
                version="v15",
                ffmpeg_path="/usr/bin",
                gpu_id=0,
                vae_type="sd-vae",
                unet_config=str(
                    self.repo_root
                    / "models/musetalkV15/musetalk.json"
                ),
                unet_model_path=str(
                    self.repo_root / "models/musetalkV15/unet.pth"
                ),
                whisper_dir=str(self.repo_root / "models/whisper"),
                inference_config="",
                bbox_shift=0,
                result_dir=str(persistent_results),
                extra_margin=10,
                fps=self.fps,
                audio_padding_length_left=2,
                audio_padding_length_right=2,
                batch_size=self.batch_size,
                output_vid_name=None,
                use_saved_coord=True,
                saved_coord=True,
                parsing_mode="jaw",
                left_cheek_width=90,
                right_cheek_width=90,
                skip_save_images=False,
            )
            runtime.args = args
            runtime.device = torch.device("cuda:0")

            runtime.vae, runtime.unet, runtime.pe = (
                runtime.load_all_model(
                    unet_model_path=args.unet_model_path,
                    vae_type=args.vae_type,
                    unet_config=args.unet_config,
                    device=runtime.device,
                )
            )
            runtime.timesteps = torch.tensor(
                [0],
                device=runtime.device,
            )
            runtime.pe = runtime.pe.half().to(runtime.device)
            runtime.vae.vae = (
                runtime.vae.vae.half().to(runtime.device)
            )
            runtime.unet.model = (
                runtime.unet.model.half().to(runtime.device)
            )

            runtime.audio_processor = runtime.AudioProcessor(
                feature_extractor_path=args.whisper_dir
            )
            runtime.weight_dtype = runtime.unet.model.dtype
            runtime.whisper = runtime.WhisperModel.from_pretrained(
                args.whisper_dir
            )
            runtime.whisper = runtime.whisper.to(
                device=runtime.device,
                dtype=runtime.weight_dtype,
            ).eval()
            runtime.whisper.requires_grad_(False)
            runtime.fp = runtime.FaceParsing(
                left_cheek_width=args.left_cheek_width,
                right_cheek_width=args.right_cheek_width,
            )

            avatar_root = (
                persistent_results
                / "v15"
                / "avatars"
                / self.avatar_id
            )
            cached = (
                (avatar_root / "avator_info.json").is_file()
                and (avatar_root / "latents.pt").is_file()
                and (avatar_root / "coords.pkl").is_file()
            )
            self._avatar = runtime.Avatar(
                avatar_id=self.avatar_id,
                video_path=str(self.source_video),
                bbox_shift=0,
                batch_size=self.batch_size,
                preparation=not cached,
            )
            self._module = runtime
        except Exception as exc:
            self._module = None
            self._avatar = None
            raise MuseTalkRuntimeUnavailable(
                "MuseTalk 1.5 load failed: "
                f"{type(exc).__name__}"
            ) from exc
        finally:
            os.chdir(previous_cwd)

    def render_sync(
        self,
        *,
        audio: bytes,
        state: AvatarState = "speaking",
    ) -> bytes:
        if not audio:
            raise ValueError("MuseTalk audio must not be empty")
        self.load()
        assert self._avatar is not None

        # Candidate v1 only drives the speaking state. The browser director
        # remains responsible for idle/listening/thinking states.
        if state != "speaking":
            state = "speaking"

        with self._render_lock:
            previous_cwd = Path.cwd()
            try:
                os.chdir(self.repo_root)
                with tempfile.TemporaryDirectory(
                    prefix="telepat-musetalk-"
                ) as tmp:
                    audio_path = Path(tmp) / "input.mp3"
                    audio_path.write_bytes(audio)
                    output_name = f"turn-{uuid4().hex}"
                    self._avatar.inference(
                        str(audio_path),
                        output_name,
                        self.fps,
                        False,
                    )
                    output_path = (
                        Path(self._avatar.video_out_path)
                        / f"{output_name}.mp4"
                    )
                    if not output_path.is_file():
                        raise RuntimeError(
                            "MuseTalk did not create an output video"
                        )
                    data = output_path.read_bytes()
                    output_path.unlink(missing_ok=True)
                    if not data:
                        raise RuntimeError(
                            "MuseTalk created an empty output video"
                        )
                    return data
            finally:
                os.chdir(previous_cwd)


class MuseTalk15Adapter:
    name = "musetalk-1.5"
    media_type = "video/mp4"

    def __init__(
        self,
        runtime: MuseTalk15Runtime | None = None,
    ) -> None:
        self.runtime = runtime or MuseTalk15Runtime()

    async def render(
        self,
        *,
        audio: bytes,
        state: AvatarState = "speaking",
    ) -> bytes:
        return await asyncio.to_thread(
            self.runtime.render_sync,
            audio=audio,
            state=state,
        )
