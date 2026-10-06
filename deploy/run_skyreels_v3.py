from __future__ import annotations

import argparse
import json
from pathlib import Path

import modal


APP_NAME = "quantareon-telepat-video-skyreels"
WORKER_CLASS = "SkyReelsV3Worker"
PREPARE_FUNCTION = "prepare_talking_avatar_model"


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "action",
        choices=["probe", "prepare", "sample-public"],
    )
    parser.add_argument("--duration", type=int, default=5)
    parser.add_argument(
        "--resolution",
        choices=["480P", "720P"],
        default="480P",
    )
    parser.add_argument("--low-vram", action="store_true")
    parser.add_argument("--output", default="skyreels-v3-sample.mp4")
    args = parser.parse_args()

    if args.action == "prepare":
        fn = modal.Function.from_name(APP_NAME, PREPARE_FUNCTION)
        result = fn.remote()
        print(json.dumps(result, indent=2, sort_keys=True))
        return

    worker_cls = modal.Cls.from_name(APP_NAME, WORKER_CLASS)
    worker = worker_cls()

    if args.action == "probe":
        result = worker.probe.remote()
        print(json.dumps(result, indent=2, sort_keys=True))
        return

    data = worker.sample_public.remote(
        duration_seconds=args.duration,
        resolution=args.resolution,
        low_vram=args.low_vram,
    )
    if not isinstance(data, bytes) or not data:
        raise RuntimeError("SkyReels sample returned no media")
    output = Path(args.output)
    output.write_bytes(data)
    print(
        json.dumps(
            {
                "ok": True,
                "output": str(output),
                "bytes": len(data),
                "duration_seconds": args.duration,
                "resolution": args.resolution,
                "low_vram": args.low_vram,
            },
            indent=2,
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
