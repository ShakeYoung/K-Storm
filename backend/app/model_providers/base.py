from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Callable


RetryCallback = Callable[[int, int, str], None]


class ModelProvider(ABC):
    @abstractmethod
    def generate(
        self,
        *,
        agent_key: str,
        system_prompt: str,
        user_prompt: str,
        max_tokens: int | None = None,
        on_retry: RetryCallback | None = None,
    ) -> str:
        raise NotImplementedError

    def label_for(self, agent_key: str) -> str:
        return "Local Mock"
