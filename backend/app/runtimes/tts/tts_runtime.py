from __future__ import annotations

from backend.app.core.capabilities import FullCapabilityReport
from backend.app.runtimes.tts.base import TTSBase
from backend.app.runtimes.tts.local_runtime import KokoroTTSRuntime


def select_tts_runtime(report: FullCapabilityReport) -> TTSBase | None:
    try:
        device = "cuda" if report.profile.cuda_available else "cpu"
        runtime: TTSBase = KokoroTTSRuntime(device=device)
        return runtime if runtime.is_available() else None
    except Exception:
        return None
