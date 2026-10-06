from __future__ import annotations

import json
import os
import time
import urllib.error
import urllib.parse
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


def health_matches_expected_build(
    health: dict,
    expected_build_sha: str,
) -> bool:
    if health.get("ok") is not True:
        return False
    if not expected_build_sha:
        return True
    return health.get("build_sha") == expected_build_sha


def main() -> None:
    base = os.environ["TELEPAT_ENDPOINT"].rstrip("/")
    expected_build_sha = os.getenv("TELEPAT_BUILD_SHA", "").strip()

    last = None
    for _ in range(12):
        try:
            status, health = request_json(
                "GET",
                base + "/health",
                timeout=15,
                transport_retries=1,
            )
            if (
                status == 200
                and health_matches_expected_build(
                    health,
                    expected_build_sha,
                )
            ):
                break

            if status == 200 and health.get("ok") is True:
                last = {
                    "reason": "build_not_converged",
                    "observed_build_sha": health.get("build_sha"),
                    "expected_build_sha": expected_build_sha,
                }
            else:
                last = (status, health)
        except Exception as exc:
            last = repr(exc)
        time.sleep(4)
    else:
        raise SystemExit(f"Health/build convergence failed: {last}")

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

    status, config_preflight = request_json(
        "GET",
        base + "/health/config-preflight",
    )
    assert status == 200, (status, config_preflight)
    assert config_preflight["ok"] is True, config_preflight

    status, production = request_json(
        "GET",
        base + "/health/production-readiness",
    )
    assert status == 200, (status, production)
    assert isinstance(production["ready"], bool)
    assert isinstance(production["blockers"], list)

    status, launch_summary = request_json(
        "GET",
        base + "/health/launch-summary",
    )
    assert status == 200, (status, launch_summary)
    assert isinstance(launch_summary["runtime_ready"], bool)
    assert isinstance(launch_summary["providers_ready"], bool)
    assert isinstance(launch_summary["site_integration_ready"], bool)

    smoke_suffix = (
        os.getenv("TELEPAT_BUILD_SHA", "local")
        .strip()
        .replace("/", "-")[:24]
        or "local"
    )
    smoke_user_id = f"live-smoke-user-{smoke_suffix}"
    smoke_session_id = f"live-smoke-session-{smoke_suffix}"

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
            "user_id": smoke_user_id,
            "session_id": smoke_session_id,
            "birth": birth,
        },
        timeout=60,
        transport_retries=3,
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
            transport_retries=3,
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
            transport_retries=3,
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
            "request_id": f"live-smoke-chat-{smoke_suffix}",
            "language": "ru",
            "user_id": bootstrap["user_id"],
            "session_id": bootstrap["session_id"],
        },
        timeout=60,
        transport_retries=3,
    )
    assert status == 200, (status, chat)
    assert chat["reply"]
    assert chat["user_id"] == bootstrap["user_id"]
    assert chat["session_id"] == bootstrap["session_id"]
    assert chat["request_id"] == f"live-smoke-chat-{smoke_suffix}"

    if readiness["conversation_ready"]:
        assert chat["provider"] != "mock", chat
    else:
        assert chat["provider"] == "mock", chat

    usage_query = urllib.parse.urlencode(
        {
            "session_id": bootstrap["session_id"],
            "user_id": bootstrap["user_id"],
        }
    )
    status, session_usage_response = request_json(
        "GET",
        base + "/session/usage?" + usage_query,
    )

    usage_observed = status == 200
    session_usage = (
        session_usage_response.get("usage") or {}
        if usage_observed
        else {}
    )
    if usage_observed:
        assert session_usage["calls"] >= 1, session_usage
        assert chat["provider"] in session_usage["providers"], session_usage
    else:
        # Like in-process latency metrics, usage counters can cold-reset if
        # Modal replaces the scale-to-zero process between requests.
        assert status == 404, (status, session_usage_response)

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
                "launch_summary": {
                    "runtime_ready": launch_summary["runtime_ready"],
                    "providers_ready": launch_summary["providers_ready"],
                    "avatar_ready": launch_summary["avatar_ready"],
                    "site_integration_ready": launch_summary[
                        "site_integration_ready"
                    ],
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
                "usage": {
                    "observed": usage_observed,
                    "calls": session_usage.get("calls"),
                    "total_tokens": session_usage.get("total_tokens"),
                    "priced_cost_usd": session_usage.get("priced_cost_usd"),
                    "fully_priced": session_usage.get("fully_priced"),
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
