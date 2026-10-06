from __future__ import annotations

import logging
import os
from time import perf_counter
from typing import Any

import httpx

from telepat.observability.metrics import runtime_metrics

from .identity import legacy_memory_user_id


logger = logging.getLogger(__name__)


class RemoteMemoryAdapter:
    """Adapter for the existing QUANTARION Memory API.

    Contract recovered from the working Platform:
      POST /api/recall
        {user_id, message, level}
      POST /api/store
        {user_id, message, response}
    """

    def __init__(self) -> None:
        self.base_url = os.getenv("MEMORY_API_URL", "").rstrip("/")
        self.api_key = os.getenv("MEMORY_API_KEY", "").strip()
        self.auth_header = os.getenv(
            "MEMORY_API_AUTH_HEADER",
            "Authorization",
        ).strip()
        self.auth_scheme = os.getenv(
            "MEMORY_API_AUTH_SCHEME",
            "Bearer",
        ).strip()
        self.recall_enabled = os.getenv(
            "TELEPAT_MEMORY_RECALL_ENABLED",
            "1",
        ).strip().lower() in {"1", "true", "yes", "on"}
        self.store_enabled = os.getenv(
            "TELEPAT_MEMORY_STORE_ENABLED",
            "1",
        ).strip().lower() in {"1", "true", "yes", "on"}

    def _headers(self) -> dict[str, str]:
        if not self.api_key or not self.auth_header:
            return {}

        value = self.api_key
        if self.auth_scheme:
            value = f"{self.auth_scheme} {self.api_key}"

        return {self.auth_header: value}

    @property
    def configured(self) -> bool:
        return bool(self.base_url)

    async def probe(self) -> dict[str, Any]:
        """Exercise the configured Memory API with a dedicated probe identity."""
        if not self.configured:
            return {
                "configured": False,
                "required": False,
                "overall_ok": True,
                "recall": {"skipped": True},
                "store": {"skipped": True},
            }

        required = self.recall_enabled and self.store_enabled
        probe_user = legacy_memory_user_id(
            "telepat-provider-probe-memory"
        )
        headers = self._headers()

        report: dict[str, Any] = {
            "configured": True,
            "required": required,
            "recall": {
                "skipped": not self.recall_enabled,
            },
            "store": {
                "skipped": not self.store_enabled,
            },
        }

        async with httpx.AsyncClient(timeout=12.0) as client:
            if self.recall_enabled:
                started = perf_counter()
                try:
                    response = await client.post(
                        f"{self.base_url}/api/recall",
                        json={
                            "user_id": probe_user,
                            "message": "TELEPAT provider health probe",
                            "level": "simple",
                        },
                        headers=headers,
                    )
                    response.raise_for_status()
                    response.json()
                    report["recall"] = {
                        "ok": True,
                        "status": response.status_code,
                    }
                    runtime_metrics.record(
                        "memory_probe_recall",
                        (perf_counter() - started) * 1000,
                        ok=True,
                        provider="remote-memory",
                    )
                except Exception as exc:
                    report["recall"] = {
                        "ok": False,
                        "error": type(exc).__name__,
                    }
                    runtime_metrics.record(
                        "memory_probe_recall",
                        (perf_counter() - started) * 1000,
                        ok=False,
                        provider="remote-memory",
                    )

            if self.store_enabled:
                started = perf_counter()
                try:
                    response = await client.post(
                        f"{self.base_url}/api/store",
                        json={
                            "user_id": probe_user,
                            "message": "TELEPAT provider health probe",
                            "response": "TELEPAT provider health probe",
                        },
                        headers=headers,
                    )
                    response.raise_for_status()
                    report["store"] = {
                        "ok": True,
                        "status": response.status_code,
                    }
                    runtime_metrics.record(
                        "memory_probe_store",
                        (perf_counter() - started) * 1000,
                        ok=True,
                        provider="remote-memory",
                    )
                except Exception as exc:
                    report["store"] = {
                        "ok": False,
                        "error": type(exc).__name__,
                    }
                    runtime_metrics.record(
                        "memory_probe_store",
                        (perf_counter() - started) * 1000,
                        ok=False,
                        provider="remote-memory",
                    )

        recall_ok = (
            not self.recall_enabled
            or bool(report["recall"].get("ok"))
        )
        store_ok = (
            not self.store_enabled
            or bool(report["store"].get("ok"))
        )
        report["overall_ok"] = recall_ok and store_ok
        return report

    async def recall(
        self,
        *,
        user_id: str,
        message: str,
        level: str = "medium",
    ) -> dict[str, Any]:
        if not self.configured or not self.recall_enabled:
            return {}

        payload = {
            "user_id": legacy_memory_user_id(user_id),
            "message": message,
            "level": level,
        }

        started = perf_counter()
        try:
            async with httpx.AsyncClient(timeout=12.0) as client:
                response = await client.post(
                    f"{self.base_url}/api/recall",
                    json=payload,
                    headers=self._headers(),
                )
                response.raise_for_status()
                data = response.json()
        except Exception as exc:
            runtime_metrics.record(
                "memory_recall",
                (perf_counter() - started) * 1000,
                ok=False,
                provider="remote-memory",
            )
            logger.warning("Memory recall unavailable: %s", type(exc).__name__)
            return {}

        runtime_metrics.record(
            "memory_recall",
            (perf_counter() - started) * 1000,
            ok=True,
            provider="remote-memory",
        )

        # Keep the rich M2 layers normalized rather than flattening everything
        # into one opaque prompt string.
        return {
            "context_text": data.get("context_text", ""),
            "facts": data.get("facts") or [],
            "emotion": data.get("emotion"),
            "insights": data.get("insights") or [],
            "semantic_context": data.get("semantic_context") or [],
            "resonance_context": data.get("resonance_context", ""),
            "pattern_summary": data.get("pattern_summary", ""),
            "recent_messages": data.get("recent_messages") or [],
            "recall_ms": data.get("recall_ms"),
        }

    async def store_exchange(
        self,
        *,
        user_id: str,
        message: str,
        response_text: str,
    ) -> None:
        if not self.configured or not self.store_enabled:
            return

        payload = {
            "user_id": legacy_memory_user_id(user_id),
            "message": message,
            "response": response_text,
        }

        started = perf_counter()
        try:
            async with httpx.AsyncClient(timeout=12.0) as client:
                response = await client.post(
                    f"{self.base_url}/api/store",
                    json=payload,
                    headers=self._headers(),
                )
                response.raise_for_status()
        except Exception as exc:
            runtime_metrics.record(
                "memory_store",
                (perf_counter() - started) * 1000,
                ok=False,
                provider="remote-memory",
            )
            # Memory failure must never break the live conversation.
            logger.warning("Memory store unavailable: %s", type(exc).__name__)
            return

        runtime_metrics.record(
            "memory_store",
            (perf_counter() - started) * 1000,
            ok=True,
            provider="remote-memory",
        )


remote_memory = RemoteMemoryAdapter()
