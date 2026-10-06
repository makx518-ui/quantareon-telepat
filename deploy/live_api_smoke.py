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
    transport_retries: int | None = None,
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

    if transport_retries is None:
        transport_retries = (
            int(os.getenv("TELEPAT_SMOKE_TRANSPORT_RETRIES", "3"))
            if method.upper() == "GET"
            else 1
        )
    transport_retries = max(1, transport_retries)

    last_error: Exception | None = None
    for attempt in range(1, transport_retries + 1):
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
        except (TimeoutError, urllib.error.URLError) as exc:
            last_error = exc
            if attempt >= transport_retries:
                raise
            time.sleep(0.5 * attempt)

    assert last_error is not None
    raise last_error


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

    status, readiness = request_json(
        "GET",
        base + "/health/readiness",
    )
    assert status == 200, (status, readiness)
    assert readiness["core_ready"] is True
    assert readiness["astro_engine_ready"] is True

    status, contract = request_json(
        "GET",
        base + "/health/provider-contract",
    )
    assert status == 200, (status, contract)
    assert "providers" in contract
    assert "capabilities" in contract

    status, production = request_json(
        "GET",
        base + "/health/production-readiness",
    )
    assert status == 200, (status, production)
    assert isinstance(production["ready"], bool)
    assert isinstance(production["blockers"], list)

    birth = {
        "year": 2000,
        "month": 1,
        "day": 1,
        "hour": 12,
        "minute": 0,
        "latitude": 0.0,
        "longitude": 0.0,
        "timezone": "UTC",
    }

    status, bootstrap = request_json(
        "POST",
        base + "/session/bootstrap",
        {
            "language": "ru",
            "birth": birth,
        },
        timeout=60,
    )
    assert status == 200, (status, bootstrap)
    assert bootstrap["user_id"]
    assert bootstrap["session_id"]

    if readiness["astro_interpreter_ready"]:
        assert bootstrap["astro_ready"] is True, bootstrap
        assert bootstrap["astro_status"] in {"ready", "cached"}, bootstrap

        status, cached_bootstrap = request_json(
            "POST",
            base + "/session/bootstrap",
            {
                "language": "ru",
                "user_id": bootstrap["user_id"],
                "session_id": bootstrap["session_id"],
                "birth": birth,
            },
            timeout=60,
        )
        assert status == 200, (status, cached_bootstrap)
        assert cached_bootstrap["astro_ready"] is True
        assert cached_bootstrap["astro_status"] == "cached"

        status, astro = request_json(
            "POST",
            base + "/session/astro",
            {
                "language": "ru",
                "user_id": bootstrap["user_id"],
                "session_id": bootstrap["session_id"],
                "birth": birth,
            },
            timeout=60,
        )
        assert status == 200, (status, astro)
        assert astro["summary"]["provider"] == "gemini"
        assert astro["summary"]["overview"]
    else:
        assert bootstrap["astro_ready"] is False
        assert bootstrap["astro_status"] == "unavailable"

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

    if readiness["conversation_ready"]:
        assert chat["provider"] != "mock", chat
    else:
        assert chat["provider"] == "mock", chat

    status, metrics = request_json(
        "GET",
        base + "/health/metrics",
    )
    assert status == 200, (status, metrics)
    assert metrics["privacy"] == "no_user_content"
    stages = metrics["stages"]

    # Metrics are intentionally in-process and bounded. Modal may replace a
    # scale-to-zero container between the chat request and this read, so an
    # empty registry is a valid cold-reset condition rather than a deploy
    # failure.
    llm_metrics = stages.get("llm") or {}
    turn_metrics = stages.get("turn_total") or {}
    metrics_observed = bool(llm_metrics and turn_metrics)

    if metrics_observed:
        assert llm_metrics["count"] >= 1, stages
        assert turn_metrics["count"] >= 1, stages

    print(
        json.dumps(
            {
                "health": health,
                "providers": providers,
                "production": {
                    "ready": production["ready"],
                    "blockers": production["blockers"],
                },
                "readiness": {
                    "core_ready": readiness["core_ready"],
                    "conversation_ready": readiness["conversation_ready"],
                    "astro_interpreter_ready": readiness["astro_interpreter_ready"],
                    "live_voice_ready": readiness["live_voice_ready"],
                    "full_telepat_ready": readiness["full_telepat_ready"],
                },
                "bootstrap": {
                    "memory_ready": bootstrap["memory_ready"],
                    "astro_ready": bootstrap["astro_ready"],
                    "astro_status": bootstrap["astro_status"],
                },
                "metrics": {
                    "observed": metrics_observed,
                    "cold_reset": not metrics_observed,
                    "llm_p50_ms": llm_metrics.get("p50_ms"),
                    "turn_p50_ms": turn_metrics.get("p50_ms"),
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
