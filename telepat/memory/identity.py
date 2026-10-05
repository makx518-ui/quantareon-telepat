from __future__ import annotations

import hashlib


def legacy_memory_user_id(user_id: str) -> int:
    """Map a browser-safe TELEPAT id to the positive integer id expected by M2.

    This is deterministic and does not fingerprint the browser. The random
    TELEPAT user_id is created by our own Session Manager and stored by the
    frontend; this function only adapts its type for the existing memory API.
    """
    digest = hashlib.blake2b(
        user_id.encode("utf-8"),
        digest_size=8,
        person=b"telepat",
    ).digest()
    value = int.from_bytes(digest, "big") & ((1 << 63) - 1)
    return value or 1
