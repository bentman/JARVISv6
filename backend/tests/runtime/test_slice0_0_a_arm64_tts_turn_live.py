from __future__ import annotations

import platform

import pytest

from backend.app.hardware.profiler import run_profiler
from backend.app.models.manager import verify_model
from backend.app.personality.loader import load_personality_profile
from backend.app.runtimes.llm.ollama_runtime import OllamaLLM
from backend.app.runtimes.tts.onnx_runtime import OnnxKokoroTTSRuntime
from backend.app.runtimes.tts.playback import has_output_device
from backend.app.runtimes.tts.tts_runtime import select_tts_runtime
from backend.app.services import voice_service
from backend.app.services.voice_service import run_voice_turn


def _is_arm64_host() -> bool:
    return platform.machine().lower() in {"arm64", "aarch64"}


def _has_input_device() -> tuple[bool, str]:
    try:
        import sounddevice as sd  # type: ignore

        devices = [d for d in sd.query_devices() if d.get("max_input_channels", 0) > 0]
        if not devices:
            return False, "no input device available"
        return True, f"devices={len(devices)}"
    except Exception as exc:
        return False, f"unable to query input devices: {exc}"


@pytest.mark.filterwarnings(
    "ignore:.*torch\\.nn\\.utils\\.weight_norm.*deprecated.*torch\\.nn\\.utils\\.parametrizations\\.weight_norm.*:FutureWarning:torch\\.nn\\.utils\\.weight_norm"
)
def test_arm64_onnx_tts_turn_live() -> None:
    if not _is_arm64_host():
        pytest.skip("ARM64-only live acceptance test")

    mic_ok, mic_reason = _has_input_device()
    assert mic_ok, f"[PREREQ FAILED] microphone: {mic_reason}"

    report = run_profiler()
    assert report.flags.tts_recommended_runtime == "onnx-kokoro"
    assert report.flags.tts_recommended_model == "kokoro-v1.0-onnx"
    assert report.flags.tts_recommended_device == "cpu"

    tts_runtime = select_tts_runtime(report)
    assert isinstance(tts_runtime, OnnxKokoroTTSRuntime)
    assert tts_runtime.device == "cpu"

    tts_model_dir = f"models/tts/{report.flags.tts_recommended_model}"
    assert verify_model(tts_model_dir, family="tts"), (
        f"[PREREQ FAILED] TTS model missing at {tts_model_dir}"
    )

    assert has_output_device(), "[PREREQ FAILED] no audio output device"
    assert OllamaLLM().is_available(), "[PREREQ FAILED] ollama unavailable"

    print("[TURN 1] microphone input expected now")
    print("[TURN 1] speak now: What is your name?")

    class _DeterministicNoBargeInDetector:
        def __init__(self, *_args, **_kwargs) -> None:
            self._failed = True
            self._failure_reason = "disabled for deterministic ARM64 acceptance"

        def start(self) -> None:
            return

        def stop(self) -> None:
            return

        @property
        def failed(self) -> bool:
            return self._failed

        @property
        def failure_reason(self) -> str:
            return self._failure_reason

    monkeypatch = pytest.MonkeyPatch()
    monkeypatch.setattr(voice_service, "BargeInDetector", _DeterministicNoBargeInDetector)

    personality = load_personality_profile("default")
    try:
        result = run_voice_turn(report, personality)
    finally:
        monkeypatch.undo()

    assert isinstance(result.response, str)
    assert len(result.response.strip()) > 0
