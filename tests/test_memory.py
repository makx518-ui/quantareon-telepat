import asyncio

from telepat.memory.adapter import MemoryAdapter
from telepat.memory.compact import compact_memory
from telepat.memory.identity import legacy_memory_user_id
from telepat.memory.remote import RemoteMemoryAdapter
from telepat.memory.service import memory_adapter


def test_legacy_id_is_stable_positive_integer() -> None:
    a = legacy_memory_user_id("same-browser-id")
    b = legacy_memory_user_id("same-browser-id")
    c = legacy_memory_user_id("other-browser-id")

    assert isinstance(a, int)
    assert a > 0
    assert a == b
    assert a != c


def test_compact_memory_limits_payload() -> None:
    memory = compact_memory(
        {
            "context_text": "x" * 10000,
            "facts": [
                {"key": "name", "value": "V" * 1000}
                for _ in range(50)
            ],
            "semantic_context": [{"text": "s" * 2000, "score": 0.9}] * 10,
            "recent_messages": [
                {"role": "user", "content": "m" * 2000}
                for _ in range(20)
            ],
        }
    )

    assert len(memory["context_text"]) <= 5001
    assert len(memory["facts"]) == 30
    assert len(memory["semantic_context"]) == 5
    assert len(memory["recent_messages"]) == 10


def test_memory_service_implements_adapter_contract() -> None:
    assert isinstance(memory_adapter, MemoryAdapter)



def test_memory_api_bearer_auth_header(monkeypatch) -> None:
    monkeypatch.setenv("MEMORY_API_URL", "https://memory.example")
    monkeypatch.setenv("MEMORY_API_KEY", "test-key")
    monkeypatch.setenv("MEMORY_API_AUTH_HEADER", "Authorization")
    monkeypatch.setenv("MEMORY_API_AUTH_SCHEME", "Bearer")

    adapter = RemoteMemoryAdapter()

    assert adapter._headers() == {
        "Authorization": "Bearer test-key",
    }


def test_memory_api_custom_header_without_scheme(monkeypatch) -> None:
    monkeypatch.setenv("MEMORY_API_URL", "https://memory.example")
    monkeypatch.setenv("MEMORY_API_KEY", "test-key")
    monkeypatch.setenv("MEMORY_API_AUTH_HEADER", "X-API-Key")
    monkeypatch.setenv("MEMORY_API_AUTH_SCHEME", "")

    adapter = RemoteMemoryAdapter()

    assert adapter._headers() == {
        "X-API-Key": "test-key",
    }



def test_memory_privacy_switches_disable_remote_calls(monkeypatch) -> None:
    monkeypatch.setenv("MEMORY_API_URL", "https://memory.example")
    monkeypatch.setenv("TELEPAT_MEMORY_RECALL_ENABLED", "0")
    monkeypatch.setenv("TELEPAT_MEMORY_STORE_ENABLED", "0")

    class _ShouldNotOpen:
        def __init__(self, *args, **kwargs) -> None:
            raise AssertionError("network client must not be created")

    monkeypatch.setattr(
        "telepat.memory.remote.httpx.AsyncClient",
        _ShouldNotOpen,
    )

    adapter = RemoteMemoryAdapter()

    recalled = asyncio.run(
        adapter.recall(
            user_id="privacy-user",
            message="secret text",
        )
    )
    stored = asyncio.run(
        adapter.store_exchange(
            user_id="privacy-user",
            message="secret text",
            response_text="reply",
        )
    )

    assert adapter.recall_enabled is False
    assert adapter.store_enabled is False
    assert recalled == {}
    assert stored is None



class _ProbeResponse:
    def __init__(self, status_code: int, payload: dict | None = None) -> None:
        self.status_code = status_code
        self._payload = payload or {}

    def raise_for_status(self) -> None:
        if self.status_code >= 400:
            raise RuntimeError(f"http {self.status_code}")

    def json(self) -> dict:
        return self._payload


class _ProbeClient:
    calls: list[str] = []

    def __init__(self, *args, **kwargs) -> None:
        pass

    async def __aenter__(self):
        type(self).calls = []
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return False

    async def post(self, url: str, **kwargs):
        type(self).calls.append(url)
        if url.endswith("/api/recall"):
            return _ProbeResponse(200, {"context_text": ""})
        if url.endswith("/api/store"):
            return _ProbeResponse(200)
        return _ProbeResponse(404)


def test_memory_probe_validates_recall_and_store(monkeypatch) -> None:
    monkeypatch.setenv("MEMORY_API_URL", "https://memory.example")
    monkeypatch.setenv("TELEPAT_MEMORY_RECALL_ENABLED", "1")
    monkeypatch.setenv("TELEPAT_MEMORY_STORE_ENABLED", "1")
    monkeypatch.setattr(
        "telepat.memory.remote.httpx.AsyncClient",
        _ProbeClient,
    )

    adapter = RemoteMemoryAdapter()
    report = asyncio.run(adapter.probe())

    assert report["configured"] is True
    assert report["required"] is True
    assert report["overall_ok"] is True
    assert report["recall"]["ok"] is True
    assert report["store"]["ok"] is True
    assert _ProbeClient.calls == [
        "https://memory.example/api/recall",
        "https://memory.example/api/store",
    ]


def test_memory_probe_does_not_open_network_when_privacy_disabled(
    monkeypatch,
) -> None:
    monkeypatch.setenv("MEMORY_API_URL", "https://memory.example")
    monkeypatch.setenv("TELEPAT_MEMORY_RECALL_ENABLED", "0")
    monkeypatch.setenv("TELEPAT_MEMORY_STORE_ENABLED", "0")

    class _ShouldNotOpen:
        def __init__(self, *args, **kwargs) -> None:
            raise AssertionError("network client must not be created")

    monkeypatch.setattr(
        "telepat.memory.remote.httpx.AsyncClient",
        _ShouldNotOpen,
    )

    adapter = RemoteMemoryAdapter()
    report = asyncio.run(adapter.probe())

    assert report["required"] is False
    assert report["overall_ok"] is True
    assert report["recall"]["skipped"] is True
    assert report["store"]["skipped"] is True
