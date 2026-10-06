from pathlib import Path

def test_modal_deployment_modules_import() -> None:
    import deploy.avatar_gpu as avatar_gpu
    import deploy.modal_app as modal_app
    import deploy.run_avatar_probe as run_avatar_probe
    import deploy.runtime as runtime
    import deploy.smoke as smoke

    assert runtime.app is not None
    assert runtime.cpu_image is not None
    assert runtime.gpu_base_image is not None
    assert avatar_gpu.avatar_app is not None
    assert avatar_gpu.app is avatar_gpu.avatar_app
    assert avatar_gpu.AvatarGPUWorker is not None
    assert avatar_gpu.app is avatar_gpu.avatar_app
    assert modal_app.web is not None
    assert modal_app.provider_probe is not None
    assert modal_app.voice_smoke_audio is not None
    assert modal_app.avatar_benchmark_audio is not None
    assert callable(run_avatar_probe.main)
    assert smoke.app is not None
    assert callable(smoke.main)


def test_modal_google_genai_spec_matches_requirements() -> None:
    import deploy.runtime as runtime

    requirements = Path("requirements.txt").read_text(encoding="utf-8")
    assert runtime.GOOGLE_GENAI_SPEC in requirements
