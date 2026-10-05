def test_modal_deployment_modules_import() -> None:
    import deploy.avatar_gpu as avatar_gpu
    import deploy.modal_app as modal_app
    import deploy.runtime as runtime
    import deploy.smoke as smoke

    assert runtime.app is not None
    assert runtime.cpu_image is not None
    assert runtime.gpu_base_image is not None
    assert avatar_gpu.AvatarGPUWorker is not None
    assert modal_app.web is not None
    assert smoke.provider_smoke is not None
