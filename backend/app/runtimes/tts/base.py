from __future__ import annotations

from abc import ABC, abstractmethod


class TTSBase(ABC):
    @abstractmethod
    def synthesize(self, text: str, output_path: str) -> str:
        raise NotImplementedError

    @abstractmethod
    def is_available(self) -> bool:
        raise NotImplementedError
