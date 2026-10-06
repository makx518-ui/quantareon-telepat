from __future__ import annotations

import os

import modal


MEMORY_SECRET_NAME = "quantareon-telepat-memory-secrets"
TELEPAT_SECRET_NAME = "quantareon-telepat-secrets"


def _upsert(name: str, values: dict[str, str]) -> None:
    existing = {
        item.name
        for item in modal.Secret.objects.list()
    }
    if name in existing:
        modal.Secret.from_name(name).update(values)
    else:
        modal.Secret.objects.create(name, values)


def provision_memory_secret() -> None:
    api_key = os.getenv("MEMORY_API_KEY", "").strip()
    if not api_key:
        raise RuntimeError("MEMORY_API_KEY is required")

    _upsert(
        MEMORY_SECRET_NAME,
        {"MEMORY_API_KEY": api_key},
    )
    print("TELEPAT Memory API secret is ready.")


def configure_telepat_memory() -> None:
    api_key = os.getenv("MEMORY_API_KEY", "").strip()
    api_url = os.getenv("MEMORY_API_URL", "").rstrip("/")
    if not api_key or not api_url:
        raise RuntimeError(
            "MEMORY_API_KEY and MEMORY_API_URL are required"
        )

    _upsert(
        TELEPAT_SECRET_NAME,
        {
            "MEMORY_API_URL": api_url,
            "MEMORY_API_KEY": api_key,
            "MEMORY_API_AUTH_HEADER": "Authorization",
            "MEMORY_API_AUTH_SCHEME": "Bearer",
            "TELEPAT_MEMORY_RECALL_ENABLED": "1",
            "TELEPAT_MEMORY_STORE_ENABLED": "1",
        },
    )
    print("TELEPAT CPU Memory provider configuration is ready.")


def main() -> None:
    mode = os.getenv("TELEPAT_MEMORY_PROVISION_MODE", "secret")
    if mode == "secret":
        provision_memory_secret()
    elif mode == "telepat":
        configure_telepat_memory()
    else:
        raise RuntimeError(f"Unknown provision mode: {mode}")


if __name__ == "__main__":
    main()
