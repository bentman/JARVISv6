from __future__ import annotations

from backend.app.core.capabilities import FullCapabilityReport
from backend.app.runtimes.tts.base import TTSBase
from backend.app.runtimes.tts.local_runtime import KokoroTTSRuntime


def _tts_cuda_usable() -> bool:
    """Return True only when the active backend environment can run TTS on CUDA."""
    try:
        import torch  # type: ignore

        return bool(torch.cuda.is_available())
    except Exception:
        return False


def select_tts_runtime(report: FullCapabilityReport) -> TTSBase | None:
    try:
        # Do not select CUDA for TTS from the host-level profiler signal alone.
        # Kokoro TTS depends on PyTorch CUDA usability inside the active backend
        # environment.
        device = "cuda" if _tts_cuda_usable() else "cpu"
        runtime: TTSBase = KokoroTTSRuntime(device=device)
        return runtime if runtime.is_available() else None
    except Exception:
        return None
