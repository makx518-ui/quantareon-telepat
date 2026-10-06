from __future__ import annotations

import json

import modal


# Compatibility launcher for the old command:
#   python -m modal run deploy/smoke.py
#
# Provider diagnostics live only in telepat/diagnostics/provider_probe.py and
# are registered on the deployed quantareon-telepat app. Keeping this shim
# prevents a second copy of provider-test logic from drifting out of sync.
app = modal.App("quantareon-telepat-smoke-client")


@app.local_entrypoint()
def main() -> None:
    probe = modal.Function.from_name(
        "quantareon-telepat",
        "provider_probe",
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
