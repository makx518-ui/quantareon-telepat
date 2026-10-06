from __future__ import annotations

import subprocess


def _parse_nvidia_smi_csv(text: str) -> dict[str, object]:
    line = next(
        (item.strip() for item in text.splitlines() if item.strip()),
        "",
    )
    if not line:
        return {
            "available": False,
            "name": None,
            "memory_total_mb": None,
            "memory_free_mb": None,
        }

    parts = [item.strip() for item in line.split(",")]
    if len(parts) < 3:
        return {
            "available": False,
            "name": None,
            "memory_total_mb": None,
            "memory_free_mb": None,
        }

    try:
        total = float(parts[1])
        free = float(parts[2])
    except ValueError:
        return {
            "available": False,
            "name": None,
            "memory_total_mb": None,
            "memory_free_mb": None,
        }

    return {
        "available": True,
        "name": parts[0],
        "memory_total_mb": round(total, 2),
        "memory_free_mb": round(free, 2),
    }


def gpu_status() -> dict[str, object]:
    try:
        completed = subprocess.run(
            [
                "nvidia-smi",
                "--query-gpu=name,memory.total,memory.free",
                "--format=csv,noheader,nounits",
            ],
            capture_output=True,
            text=True,
            timeout=5,
            check=True,
        )
    except Exception as exc:
        return {
            "available": False,
            "name": None,
            "memory_total_mb": None,
            "memory_free_mb": None,
            "error": type(exc).__name__,
        }

    return _parse_nvidia_smi_csv(completed.stdout)
