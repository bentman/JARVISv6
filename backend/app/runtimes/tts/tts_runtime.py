from __future__ import annotations

from backend.app.core.capabilities import FullCapabilityReport
from backend.app.runtimes.tts.base import TTSBase
from backend.app.runtimes.tts.local_runtime import LocalTTSRuntime
from backend.app.runtimes.tts.onnx_runtime import OnnxKokoroTTSRuntime


def select_tts_runtime(report: FullCapabilityReport) -> TTSBase | None:
    try:
        runtime_family = report.flags.tts_recommended_runtime
        if runtime_family not in {"kokoro", "onnx-kokoro"}:
            return None

        if report.flags.tts_recommended_device not in {"cuda", "cpu"}:
            return None

        if runtime_family == "kokoro":
            runtime: TTSBase = LocalTTSRuntime(
                model_name=report.flags.tts_recommended_model,
                device=report.flags.tts_recommended_device,
            )
        else:
            runtime = OnnxKokoroTTSRuntime(
                model_name=report.flags.tts_recommended_model,
                device=report.flags.tts_recommended_device,
            )
        return runtime if runtime.is_available() else None
    except Exception:
        return None
