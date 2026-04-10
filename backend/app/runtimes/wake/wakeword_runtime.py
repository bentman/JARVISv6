from __future__ import annotations

from backend.app.core import settings
from backend.app.runtimes.wake.base import WakeWordBase
from backend.app.runtimes.wake.local_runtime import PorcupineWakeWord


def select_wake_runtime(
    access_key: str | None = None,
    model_path: str | None = None,
) -> WakeWordBase | None:
    runtime = PorcupineWakeWord(
        access_key=access_key if access_key is not None else settings.PICOVOICE_ACCESS_KEY,
        model_path=model_path if model_path is not None else settings.PVPORCUPINE_MODEL_PATH,
    )
    if not runtime.is_available():
        return None
    return runtime
