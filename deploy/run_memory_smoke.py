from __future__ import annotations

import json
import os
from uuid import uuid4

import httpx


def main() -> None:
    base = os.environ["MEMORY_API_URL"].rstrip("/")
    key = os.environ["MEMORY_API_KEY"].strip()
    if not key:
        raise RuntimeError("MEMORY_API_KEY is required")

    headers = {"Authorization": f"Bearer {key}"}
    user_id = 900_000_000 + (uuid4().int % 90_000_000)
    marker = f"telepat-memory-smoke-{uuid4().hex[:12]}"

    with httpx.Client(timeout=20.0) as client:
        health = client.get(f"{base}/health")
        health.raise_for_status()

        stored = client.post(
            f"{base}/api/store",
            headers=headers,
            json={
                "user_id": user_id,
                "message": f"Remember marker {marker}",
                "response": f"Stored marker {marker}",
            },
        )
        stored.raise_for_status()

        recalled = client.post(
            f"{base}/api/recall",
            headers=headers,
            json={
                "user_id": user_id,
                "message": marker,
                "level": "deep",
            },
        )
        recalled.raise_for_status()
        payload = recalled.json()

    context = str(payload.get("context_text") or "")
    if marker not in context:
        raise RuntimeError("Memory recall did not return stored exchange")

    print(
        json.dumps(
            {
                "health": health.json(),
                "store_ok": True,
                "recall_ok": True,
                "context_chars": len(context),
                "semantic_items": len(
                    payload.get("semantic_context") or []
                ),
                "recent_messages": len(
                    payload.get("recent_messages") or []
                ),
            },
            ensure_ascii=False,
        )
    )


if __name__ == "__main__":
    main()
