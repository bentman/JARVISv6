from __future__ import annotations

import pytest

from backend.app.hardware.profiler import run_profiler
from backend.app.models.manager import verify_model
from backend.app.personality.loader import load_personality_profile
from backend.app.runtimes.llm.ollama_runtime import OllamaLLM
from backend.app.services.voice_service import run_voice_turn


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
def test_voice_turn_live() -> None:
    mic_ok, mic_reason = _has_input_device()
    assert mic_ok, f"[PREREQ FAILED] microphone: {mic_reason}"

    print("[TURN 1] microphone input expected now")
    print("[TURN 1] speak now: What is your name?")

    report = run_profiler()
    model_name = report.flags.stt_recommended_model
    local_model_dir = f"models/stt/{model_name}"
    stt_model_present = verify_model(local_model_dir)
    assert (
        stt_model_present
    ), f"[PREREQ FAILED] stt model missing: {model_name} at {local_model_dir}"

    ollama_ok = OllamaLLM().is_available()
    assert ollama_ok, "[PREREQ FAILED] ollama: OllamaLLM unavailable"

    personality = load_personality_profile("default")
    result = run_voice_turn(report, personality)
    response = result.response

    assert isinstance(response, str)
    assert len(response.strip()) > 0
