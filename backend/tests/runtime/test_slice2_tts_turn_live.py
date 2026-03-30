from __future__ import annotations

from backend.app.hardware.profiler import run_profiler
from backend.app.models.manager import verify_model
from backend.app.personality.loader import load_personality_profile
from backend.app.runtimes.llm.ollama_runtime import OllamaLLM
from backend.app.runtimes.tts.playback import has_output_device
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


def test_spoken_voice_turn_live() -> None:
    mic_ok, mic_reason = _has_input_device()
    assert mic_ok, f"[PREREQ FAILED] microphone: {mic_reason}"

    report = run_profiler()

    stt_model_dir = f"models/stt/{report.flags.stt_recommended_model}"
    assert verify_model(stt_model_dir), f"[PREREQ FAILED] STT model missing at {stt_model_dir}"

    assert verify_model(
        "models/tts/kokoro-v1.0",
        family="tts",
    ), "[PREREQ FAILED] TTS model missing at models/tts/kokoro-v1.0"

    assert has_output_device(), "[PREREQ FAILED] no audio output device"

    assert OllamaLLM().is_available(), "[PREREQ FAILED] ollama unavailable"

    personality = load_personality_profile("default")
    response = run_voice_turn(report, personality)

    assert isinstance(response, str)
    assert len(response.strip()) > 0
