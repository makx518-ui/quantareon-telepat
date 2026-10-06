from __future__ import annotations

import json
import os

import modal


APP_NAME = "quantareon-telepat-avatar-musetalk"
CLASS_NAME = "MuseTalkBenchmarkWorker"


def main() -> None:
    runs = max(
        1,
        int(os.getenv("TELEPAT_AVATAR_BENCHMARK_RUNS", "3")),
    )
    warmup_runs = max(
        0,
        int(os.getenv("TELEPAT_AVATAR_BENCHMARK_WARMUPS", "1")),
    )
    worker = modal.Cls.from_name(APP_NAME, CLASS_NAME)
    result = worker().benchmark.remote(
        runs=runs,
        warmup_runs=warmup_runs,
    )
    print(json.dumps(result, ensure_ascii=False, indent=2))
    if not result.get("ok"):
        raise SystemExit("MuseTalk TELEPAT benchmark failed")


if __name__ == "__main__":
    main()
