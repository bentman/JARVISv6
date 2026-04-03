from __future__ import annotations

import threading
from typing import Any

import numpy as np
import sounddevice as sd


class BargeInDetector:
    """Listens for barge-in speech energy on the default input device."""

    def __init__(
        self,
        interrupt_flag: threading.Event,
        *,
        threshold: float = 0.02,
        min_trigger_frames: int = 3,
        sample_rate: int = 16000,
        block_size: int = 1024,
    ) -> None:
        self._interrupt_flag = interrupt_flag
        self._threshold = threshold
        self._min_trigger_frames = min_trigger_frames
        self._sample_rate = sample_rate
        self._block_size = block_size
        self._stream: Any | None = None
        self._consecutive_trigger_frames = 0
        self._failed = False
        self._failure_reason: str | None = None

    def _callback(self, indata: np.ndarray, frames: int, time_info: Any, status: Any) -> None:
        try:
            rms = float(np.sqrt(np.mean(indata**2)))
            if rms >= self._threshold:
                self._consecutive_trigger_frames += 1
            else:
                self._consecutive_trigger_frames = 0

            if self._consecutive_trigger_frames >= self._min_trigger_frames:
                self._interrupt_flag.set()
        except Exception as exc:
            self._failed = True
            self._failure_reason = str(exc)

    def start(self) -> None:
        try:
            self._stream = sd.InputStream(
                callback=self._callback,
                samplerate=self._sample_rate,
                blocksize=self._block_size,
                channels=1,
                dtype="float32",
            )
            self._stream.start()
        except Exception as exc:
            self._failed = True
            self._failure_reason = str(exc)
            self._stream = None

    def stop(self) -> None:
        stream = self._stream
        self._stream = None
        if stream is None:
            return
        try:
            stream.stop()
            stream.close()
        except Exception as exc:
            self._failed = True
            self._failure_reason = str(exc)

    @property
    def failed(self) -> bool:
        return self._failed

    @property
    def failure_reason(self) -> str | None:
        return self._failure_reason
