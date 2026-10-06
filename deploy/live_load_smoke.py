from __future__ import annotations

import concurrent.futures
import json
import os
import statistics
import time
import urllib.error
import urllib.request


def request_json(
    method: str,
    url: str,
    payload: dict | None = None,
    *,
    timeout: int = 30,
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


def percentile(values: list[float], fraction: float) -> float:
    ordered = sorted(values)
    if not ordered:
        return 0.0
    index = round((len(ordered) - 1) * fraction)
    return ordered[index]


def one_chat(base: str, index: int) -> dict[str, object]:
    started = time.perf_counter()
    payload = {
        "message": f"core load smoke {index}",
        "language": "ru",
        "user_id": f"load-user-{index}",
        "session_id": f"load-session-{index}",
    }

    transport_retries = int(
        os.getenv("TELEPAT_CORE_LOAD_TRANSPORT_RETRIES", "3")
    )
    last_error: Exception | None = None
    status = 0
    data: dict = {}

    for attempt in range(1, transport_retries + 1):
        try:
            status, data = request_json(
                "POST",
                base + "/chat",
                payload,
                timeout=30,
            )
            last_error = None
            break
        except (TimeoutError, urllib.error.URLError) as exc:
            last_error = exc
            if attempt >= transport_retries:
                break
            time.sleep(0.5 * attempt)

    if last_error is not None:
        raise RuntimeError(
            f"chat {index} transport failed after "
            f"{transport_retries} attempts: {type(last_error).__name__}"
        ) from last_error

    elapsed_ms = (time.perf_counter() - started) * 1000

    if status != 200:
        raise RuntimeError(
            f"chat {index} failed: status={status} payload={data}"
        )
    if not data.get("reply"):
        raise RuntimeError(f"chat {index} returned no reply")
    if data.get("provider") != "mock":
        raise RuntimeError(
            f"core load smoke expected mock, got {data.get('provider')}"
        )

    return {
        "session_id": data.get("session_id"),
        "latency_ms": elapsed_ms,
    }


def main() -> None:
    base = os.environ["TELEPAT_ENDPOINT"].rstrip("/")

    status, readiness = request_json(
        "GET",
        base + "/health/readiness",
    )
    if status != 200:
        raise SystemExit(
            f"readiness failed: status={status} payload={readiness}"
        )

    if readiness.get("conversation_ready"):
        print(
            json.dumps(
                {
                    "skipped": True,
                    "reason": "real_conversation_provider_configured",
                }
            )
        )
        return

    request_count = int(
        os.getenv("TELEPAT_CORE_LOAD_REQUESTS", "12")
    )
    workers = min(
        request_count,
        int(os.getenv("TELEPAT_CORE_LOAD_CONCURRENCY", "4")),
    )

    with concurrent.futures.ThreadPoolExecutor(
        max_workers=workers,
    ) as pool:
        futures = [
            pool.submit(one_chat, base, index)
            for index in range(request_count)
        ]
        results = [future.result() for future in futures]

    session_ids = {
        str(item["session_id"])
        for item in results
    }
    if len(session_ids) != request_count:
        raise SystemExit("load smoke did not preserve independent sessions")

    latencies = [
        float(item["latency_ms"])
        for item in results
    ]

    print(
        json.dumps(
            {
                "skipped": False,
                "requests": request_count,
                "concurrency": workers,
                "successes": len(results),
                "p50_ms": round(percentile(latencies, 0.50), 2),
                "p95_ms": round(percentile(latencies, 0.95), 2),
                "max_ms": round(max(latencies), 2),
                "mean_ms": round(statistics.fmean(latencies), 2),
            }
        )
    )


if __name__ == "__main__":
    main()
