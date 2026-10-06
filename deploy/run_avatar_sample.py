from __future__ import annotations

import argparse
from pathlib import Path

import modal


CANDIDATES = {
    "musetalk": (
        "quantareon-telepat-avatar-musetalk",
        "MuseTalkBenchmarkWorker",
    ),
    "latentsync": (
        "quantareon-telepat-avatar-latentsync",
        "LatentSyncBenchmarkWorker",
    ),
}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "candidate",
        choices=sorted(CANDIDATES),
    )
    parser.add_argument("output")
    args = parser.parse_args()

    app_name, class_name = CANDIDATES[args.candidate]
    worker = modal.Cls.from_name(app_name, class_name)
    data = worker().sample.remote()
    if not isinstance(data, bytes) or not data:
        raise RuntimeError("Avatar sample contained no media")

    output = Path(args.output)
    output.write_bytes(data)
    print(
        f"{args.candidate} sample saved: "
        f"{output} ({len(data)} bytes)"
    )


if __name__ == "__main__":
    main()
