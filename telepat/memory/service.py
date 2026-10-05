from __future__ import annotations

from .adapter import MemoryAdapter
from .remote import remote_memory


# Core TELEPAT modules depend only on this adapter boundary.
# The concrete remote QUANTARION Memory API can be replaced later without
# changing the orchestrator or session bootstrap code.
memory_adapter: MemoryAdapter = remote_memory
