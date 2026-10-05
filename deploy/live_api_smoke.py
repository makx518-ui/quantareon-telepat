from __future__ import annotations

import json
import os
import time
import urllib.error
import urllib.request


def request_json(
    method: str,
    url: str,
    payload: dict | None = None,
    *,
    timeout: int = 20,
) -> tuple[int, dict]:
    body = None
    headers = {"Accept": "application/json"}
    if payload is not None:
        body = json.dumps(payload).encode("utf-8")
        headers["Content-Type"] = "application/json"

    req = urllib.request.Request(
        url,
        data=body,
        headers=headers,
        method=method,
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as response:
            data = json.loads(response.read().decode("utf-8"))
            return response.status, data
    except urllib.error.HTTPError as exc:
        raw = exc.read().decode("utf-8", errors="replace")
        try:
            data = json.loads(raw)
        except Exception:
            data = {"raw": raw}
        return exc.code, data


def main() -> None:
    base = os.environ["TELEPAT_ENDPOINT"].rstrip("/")

    last = None
    for _ in range(6):
        try:
            status, health = request_json("GET", base + "/health", timeout=15)
            if status == 200 and health.get("ok") is True:
                break
            last = (status, health)
        except Exception as exc:
            last = repr(exc)
        time.sleep(4)
    else:
        raise SystemExit(f"Health check failed: {last}")

    status, providers = request_json(
        "GET",
        base + "/health/providers",
    )
    assert status == 200, (status, providers)
    assert providers
    assert all(isinstance(value, bool) for value in providers.values())

    status, bootstrap = request_json(
        "POST",
        base + "/session/bootstrap",
        {
            "language": "ru",
            "birth": {
                "year": 2000,
                "month": 1,
                "day": 1,
                "hour": 12,
                "minute": 0,
                "latitude": 0.0,
                "longitude": 0.0,
                "timezone": "UTC",
            },
        },
        timeout=60,
    )
    assert status == 200, (status, bootstrap)
    assert bootstrap["user_id"]
    assert bootstrap["session_id"]
    assert bootstrap["astro_status"] in {
        "ready",
        "cached",
        "unavailable",
    }

    status, chat = request_json(
        "POST",
        base + "/chat",
        {
            "message": "Привет, TELEPAT.",
            "language": "ru",
            "user_id": bootstrap["user_id"],
            "session_id": bootstrap["session_id"],
        },
        timeout=60,
    )
    assert status == 200, (status, chat)
    assert chat["reply"]
    assert chat["user_id"] == bootstrap["user_id"]
    assert chat["session_id"] == bootstrap["session_id"]

    print(
        json.dumps(
            {
                "health": health,
                "providers": providers,
                "bootstrap": {
                    "memory_ready": bootstrap["memory_ready"],
                    "astro_ready": bootstrap["astro_ready"],
                    "astro_status": bootstrap["astro_status"],
                },
                "chat": {
                    "provider": chat["provider"],
                    "intent": chat["intent"],
                    "avatar_state": chat["avatar_state"],
                    "reply_chars": len(chat["reply"]),
                },
            },
            ensure_ascii=False,
        )
    )


if __name__ == "__main__":
    main()
