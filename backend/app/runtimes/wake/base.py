from __future__ import annotations

import threading
from abc import ABC, abstractmethod


class WakeWordBase(ABC):
    @abstractmethod
    def start(self, wake_flag: threading.Event) -> None:
        """Begin listening. Set wake_flag when keyword is detected."""
        raise NotImplementedError

    @abstractmethod
    def stop(self) -> None:
        raise NotImplementedError

    @abstractmethod
    def is_available(self) -> bool:
        raise NotImplementedError

    @property
    @abstractmethod
    def failed(self) -> bool:
        raise NotImplementedError

    @property
    @abstractmethod
    def failure_reason(self) -> str | None:
        raise NotImplementedError
