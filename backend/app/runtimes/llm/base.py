from __future__ import annotations

from abc import ABC, abstractmethod


class LLMBase(ABC):
    @abstractmethod
    def complete(self, prompt: str) -> str:
        raise NotImplementedError

    @abstractmethod
    def is_available(self) -> bool:
        raise NotImplementedError
