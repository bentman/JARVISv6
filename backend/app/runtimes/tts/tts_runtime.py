from __future__ import annotations

from backend.app.core.capabilities import FullCapabilityReport
from backend.app.runtimes.tts.base import TTSBase
from backend.app.runtimes.tts.local_runtime import LocalTTSRuntime


def select_tts_runtime(report: FullCapabilityReport) -> TTSBase | None:
    try:
        if report.flags.tts_recommended_runtime != "kokoro":
            return None

        runtime: TTSBase = LocalTTSRuntime(
            model_name=report.flags.tts_recommended_model,
            device=report.flags.tts_recommended_device,
        )
        return runtime if runtime.is_available() else None
    except Exception:
        return None
