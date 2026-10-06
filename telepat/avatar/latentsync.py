from __future__ import annotations

import asyncio
import os
import sys
import tempfile
import threading
from pathlib import Path

from .assets import source_video_path
from .states import AvatarState


class LatentSyncRuntimeUnavailable(RuntimeError):
    pass


class LatentSync16Runtime:
    """Pinned LatentSync 1.6 runtime behind TELEPAT's AvatarAdapter."""

    name = "latentsync-1.6"
    media_type = "video/mp4"

    def __init__(
        self,
        *,
        repo_root: str | Path = "/opt/LatentSync",
        source_video: str | Path | None = None,
        inference_steps: int = 20,
        guidance_scale: float = 1.5,
    ) -> None:
        self.repo_root = Path(repo_root)
        self.source_video = (
            Path(source_video) if source_video else source_video_path()
        )
        self.inference_steps = int(inference_steps)
        self.guidance_scale = float(guidance_scale)
        self._pipeline = None
        self._config = None
        self._dtype = None
        self._helper = None
        self._render_lock = threading.Lock()

    @property
    def loaded(self) -> bool:
        return self._pipeline is not None

    def load(self) -> None:
        if self.loaded:
            return
        if not self.repo_root.is_dir():
            raise LatentSyncRuntimeUnavailable(
                f"LatentSync repository missing: {self.repo_root}"
            )
        if not self.source_video.is_file():
            raise LatentSyncRuntimeUnavailable(
                f"Avatar source video missing: {self.source_video}"
            )

        repo_text = str(self.repo_root)
        if repo_text not in sys.path:
            sys.path.insert(0, repo_text)

        previous_cwd = Path.cwd()
        try:
            os.chdir(self.repo_root)
            import torch
            from accelerate.utils import set_seed
            from DeepCache import DeepCacheSDHelper
            from diffusers import AutoencoderKL, DDIMScheduler
            from omegaconf import OmegaConf

            from latentsync.models.unet import UNet3DConditionModel
            from latentsync.pipelines.lipsync_pipeline import (
                LipsyncPipeline,
            )
            from latentsync.whisper.audio2feature import Audio2Feature

            config = OmegaConf.load(
                "configs/unet/stage2_512.yaml"
            )
            dtype = (
                torch.float16
                if torch.cuda.is_available()
                and torch.cuda.get_device_capability()[0] > 7
                else torch.float32
            )
            scheduler = DDIMScheduler.from_pretrained("configs")

            cross_attention_dim = int(
                config.model.cross_attention_dim
            )
            if cross_attention_dim == 768:
                whisper_model = "checkpoints/whisper/small.pt"
            elif cross_attention_dim == 384:
                whisper_model = "checkpoints/whisper/tiny.pt"
            else:
                raise RuntimeError(
                    "Unsupported LatentSync cross_attention_dim"
                )

            audio_encoder = Audio2Feature(
                model_path=whisper_model,
                device="cuda",
                num_frames=config.data.num_frames,
                audio_feat_length=config.data.audio_feat_length,
            )
            vae = AutoencoderKL.from_pretrained(
                "stabilityai/sd-vae-ft-mse",
                torch_dtype=dtype,
            )
            vae.config.scaling_factor = 0.18215
            vae.config.shift_factor = 0

            unet, _ = UNet3DConditionModel.from_pretrained(
                OmegaConf.to_container(config.model),
                "checkpoints/latentsync_unet.pt",
                device="cpu",
            )
            unet = unet.to(dtype=dtype)

            pipeline = LipsyncPipeline(
                vae=vae,
                audio_encoder=audio_encoder,
                unet=unet,
                scheduler=scheduler,
            ).to("cuda")

            helper = DeepCacheSDHelper(pipe=pipeline)
            helper.set_params(
                cache_interval=3,
                cache_branch_id=0,
            )
            helper.enable()
            set_seed(1247)

            self._pipeline = pipeline
            self._config = config
            self._dtype = dtype
            self._helper = helper
        except Exception as exc:
            self._pipeline = None
            self._config = None
            self._dtype = None
            self._helper = None
            raise LatentSyncRuntimeUnavailable(
                "LatentSync 1.6 load failed: "
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
            raise ValueError("LatentSync audio must not be empty")
        self.load()
        assert self._pipeline is not None
        assert self._config is not None
        assert self._dtype is not None

        if state != "speaking":
            state = "speaking"

        with self._render_lock:
            previous_cwd = Path.cwd()
            try:
                os.chdir(self.repo_root)
                with tempfile.TemporaryDirectory(
                    prefix="telepat-latentsync-"
                ) as tmp:
                    root = Path(tmp)
                    audio_path = root / "input.mp3"
                    output_path = root / "output.mp4"
                    temp_dir = root / "work"
                    audio_path.write_bytes(audio)

                    self._pipeline(
                        video_path=str(self.source_video),
                        audio_path=str(audio_path),
                        video_out_path=str(output_path),
                        num_frames=self._config.data.num_frames,
                        num_inference_steps=self.inference_steps,
                        guidance_scale=self.guidance_scale,
                        weight_dtype=self._dtype,
                        width=self._config.data.resolution,
                        height=self._config.data.resolution,
                        mask_image_path=(
                            self._config.data.mask_image_path
                        ),
                        temp_dir=str(temp_dir),
                    )
                    if not output_path.is_file():
                        raise RuntimeError(
                            "LatentSync did not create an output video"
                        )
                    data = output_path.read_bytes()
                    if not data:
                        raise RuntimeError(
                            "LatentSync created an empty output video"
                        )
                    return data
            finally:
                os.chdir(previous_cwd)


class LatentSync16Adapter:
    name = "latentsync-1.6"
    media_type = "video/mp4"

    def __init__(
        self,
        runtime: LatentSync16Runtime | None = None,
    ) -> None:
        self.runtime = runtime or LatentSync16Runtime(
            inference_steps=int(
                os.getenv(
                    "TELEPAT_LATENTSYNC_INFERENCE_STEPS",
                    "20",
                )
            ),
            guidance_scale=float(
                os.getenv(
                    "TELEPAT_LATENTSYNC_GUIDANCE_SCALE",
                    "1.5",
                )
            ),
        )

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
