from __future__ import annotations

from abc import ABC, abstractmethod

from telepat.core.models import ContextPacket


class ConversationProvider(ABC):
    name: str = "unknown"

    @property
    def configured(self) -> bool:
        return True

    @abstractmethod
    async def generate(self, context: ContextPacket) -> str:
        raise NotImplementedError
