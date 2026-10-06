from __future__ import annotations

import json

import modal


APP_NAME = "quantareon-telepat"
FUNCTION_NAME = "provider_probe"


def main() -> None:
    probe = modal.Function.from_name(
        APP_NAME,
        FUNCTION_NAME,
    )
    result = probe.remote()

    print(
        json.dumps(
            result,
            ensure_ascii=False,
            indent=2,
        )
    )

    if not result.get("overall_ok"):
        raise SystemExit(
            "TELEPAT provider probe failed: "
            + ", ".join(
                result.get("required_failures") or []
            )
        )


if __name__ == "__main__":
    main()
