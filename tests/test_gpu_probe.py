from telepat.avatar.gpu_probe import _parse_nvidia_smi_csv


def test_gpu_probe_parses_nvidia_smi_csv() -> None:
    status = _parse_nvidia_smi_csv(
        "NVIDIA L4, 23034, 22000\n"
    )

    assert status == {
        "available": True,
        "name": "NVIDIA L4",
        "memory_total_mb": 23034.0,
        "memory_free_mb": 22000.0,
    }


def test_gpu_probe_rejects_malformed_output() -> None:
    status = _parse_nvidia_smi_csv("not-valid")

    assert status["available"] is False
    assert status["name"] is None
