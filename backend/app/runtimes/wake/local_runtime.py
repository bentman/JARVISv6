from __future__ import annotations

import threading
from pathlib import Path
from typing import Any

import numpy as np

from backend.app.runtimes.wake.base import WakeWordBase


class PorcupineWakeWord(WakeWordBase):
    def __init__(
        self,
        *,
        access_key: str | None,
        model_path: str | None,
        keyword_paths: list[str] | None = None,
    ) -> None:
        self._access_key = (access_key or "").strip()
        self._model_path = model_path or ""
        self._keyword_paths = keyword_paths
        self._wake_flag: threading.Event | None = None
        self._stream: Any | None = None
        self._porcupine: Any | None = None
        self._failed = False
        self._failure_reason: str | None = None

    def is_available(self) -> bool:
        if not self._access_key:
            return False
        if self._model_path and not Path(self._model_path).exists():
            return False
        try:
            import pvporcupine  # type: ignore  # noqa: F401
            import sounddevice  # type: ignore  # noqa: F401

            return True
        except Exception:
            return False

    def _set_failure(self, reason: str) -> None:
        self._failed = True
        self._failure_reason = reason

    def _callback(self, indata: np.ndarray, frames: int, time_info: Any, status: Any) -> None:
        del frames, time_info, status
        try:
            if self._porcupine is None or self._wake_flag is None:
                return
            pcm = np.asarray(indata).flatten().astype(np.int16).tolist()
            keyword_index = int(self._porcupine.process(pcm))
            if keyword_index >= 0:
                self._wake_flag.set()
        except Exception as exc:
            self._set_failure(str(exc))

    def start(self, wake_flag: threading.Event) -> None:
        self._wake_flag = wake_flag

        if not self._access_key:
            self._set_failure("PICOVOICE_ACCESS_KEY is not set")
            return
        if self._model_path and not Path(self._model_path).exists():
            self._set_failure(f"PVPORCUPINE_MODEL_PATH does not exist: {self._model_path}")
            return

        try:
            import pvporcupine  # type: ignore
            import sounddevice as sd  # type: ignore

            create_kwargs: dict[str, Any] = {
                "access_key": self._access_key,
            }
            if self._keyword_paths:
                create_kwargs["keyword_paths"] = self._keyword_paths
            elif self._model_path:
                create_kwargs["keyword_paths"] = [self._model_path]
            else:
                create_kwargs["keywords"] = ["jarvis"]

            self._porcupine = pvporcupine.create(**create_kwargs)
            if self._porcupine is None:
                self._set_failure("porcupine create returned None")
                return

            sample_rate = int(self._porcupine.sample_rate)
            frame_length = int(self._porcupine.frame_length)
            self._stream = sd.InputStream(
                callback=self._callback,
                samplerate=sample_rate,
                blocksize=frame_length,
                channels=1,
                dtype="int16",
            )
            self._stream.start()
        except Exception as exc:
            self._set_failure(str(exc))
            self.stop()

    def stop(self) -> None:
        stream = self._stream
        self._stream = None
        if stream is not None:
            try:
                stream.stop()
                stream.close()
            except Exception as exc:
                self._set_failure(str(exc))

        porcupine = self._porcupine
        self._porcupine = None
        if porcupine is not None:
            try:
                porcupine.delete()
            except Exception as exc:
                self._set_failure(str(exc))

    @property
    def failed(self) -> bool:
        return self._failed

    @property
    def failure_reason(self) -> str | None:
        return self._failure_reason
