from __future__ import annotations

import pytest

from backend.app.artifacts.storage import list_session_turns, read_turn_artifact
from backend.app.conversation.session_manager import SessionManager
from backend.app.hardware.profiler import run_profiler
from backend.app.memory.working import WorkingMemory
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


@pytest.mark.filterwarnings(
    "ignore:.*torch\\.nn\\.utils\\.weight_norm.*deprecated.*torch\\.nn\\.utils\\.parametrizations\\.weight_norm.*:FutureWarning:torch\\.nn\\.utils\\.weight_norm"
)
def test_multiturn_voice_session_live() -> None:
    mic_ok, mic_reason = _has_input_device()
    assert mic_ok, f"[PREREQ FAILED] microphone: {mic_reason}"

    report = run_profiler()
    personality = load_personality_profile("default")

    stt_model_dir = f"models/stt/{report.flags.stt_recommended_model}"
    assert verify_model(stt_model_dir), f"[PREREQ FAILED] STT model missing at {stt_model_dir}"

    assert verify_model(
        "models/tts/kokoro-v1.0",
        family="tts",
    ), "[PREREQ FAILED] TTS model missing at models/tts/kokoro-v1.0"

    assert has_output_device(), "[PREREQ FAILED] no audio output device"
    assert OllamaLLM().is_available(), "[PREREQ FAILED] ollama unavailable"

    session = SessionManager.open_session()
    memory = WorkingMemory(max_turns=5)
    print(f"[SESSION] opened: {session.session_id}")

    print("[TURN 1] speak now: My codename is JARVIS.")
    response1 = run_voice_turn(report, personality, session=session, memory=memory)
    print(f"[TURN 1] response: {response1}")
    print(f"[TURN 1] memory_turns: {len(memory.get_context_turns())}")

    print("[TURN 2] speak now: What codename did I give you?")
    response2 = run_voice_turn(report, personality, session=session, memory=memory)
    print(f"[TURN 2] response: {response2}")
    print(f"[TURN 2] memory_turns: {len(memory.get_context_turns())}")

    turn_ids = list_session_turns(session.session_id)
    artifact1 = read_turn_artifact(session.session_id, turn_ids[0])
    artifact2 = read_turn_artifact(session.session_id, turn_ids[1])

    session = SessionManager.close_session(session)
    print(f"[SESSION] closed: {session.ended_at}")

    assert len(turn_ids) == 2
    assert len(memory.get_context_turns()) == 2
    assert session.turn_count == 2
    assert session.ended_at is not None
    assert isinstance(response1, str) and len(response1.strip()) > 0
    assert isinstance(response2, str) and len(response2.strip()) > 0
    assert artifact2.input_modality == "voice"
    assert artifact1.transcript in artifact2.prompt_text
    assert artifact2.transcript in artifact2.prompt_text
