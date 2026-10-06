from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field

from telepat.core.models import ContextPacket


@dataclass(frozen=True, slots=True)
class ProviderUsage:
    input_tokens: int = 0
    output_tokens: int = 0
    cached_input_tokens: int = 0
    thought_tokens: int = 0

    @property
    def total_tokens(self) -> int:
        return (
            self.input_tokens
            + self.output_tokens
            + self.thought_tokens
        )


@dataclass(frozen=True, slots=True)
class ConversationResult:
    text: str
    model: str
    usage: ProviderUsage = field(default_factory=ProviderUsage)


class ConversationProvider(ABC):
    name: str = "unknown"

    @property
    def configured(self) -> bool:
        return True

    @abstractmethod
    async def generate(
        self,
        context: ContextPacket,
    ) -> ConversationResult:
        raise NotImplementedError
