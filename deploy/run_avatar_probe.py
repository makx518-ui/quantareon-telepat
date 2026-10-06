from __future__ import annotations

import json

import modal


APP_NAME = "quantareon-telepat"
CLASS_NAME = "AvatarGPUWorker"


def main() -> None:
    avatar_cls = modal.Cls.from_name(
        APP_NAME,
        CLASS_NAME,
    )
    result = avatar_cls().probe.remote()

    print(
        json.dumps(
            result,
            ensure_ascii=False,
            indent=2,
        )
    )

    if not result.get("ok"):
        raise SystemExit("TELEPAT avatar GPU probe failed")


if __name__ == "__main__":
    main()
