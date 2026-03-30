from __future__ import annotations

from abc import ABC, abstractmethod


class STTBase(ABC):
    @abstractmethod
    def transcribe(self, audio_path: str) -> str:
        raise NotImplementedError

    @abstractmethod
    def is_available(self) -> bool:
        raise NotImplementedError
