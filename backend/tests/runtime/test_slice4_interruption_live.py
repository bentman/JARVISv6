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
def test_barge_in_live() -> None:
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

    print("[TURN 1][BASELINE] microphone input expected now")
    print("[TURN 1][BASELINE] speak now: What is your name?")
    print("[TURN 1][BASELINE] after you finish speaking, remain silent while JARVIS speaks")
    result1 = run_voice_turn(report, personality, session=session, memory=memory)
    assert not result1.interrupted, "[PREREQ FAILED] turn 1 was interrupted before turn 2 could begin"
    assert result1.response and len(result1.response.strip()) > 0
    print(f"[TURN 1] response: {result1.response}")

    print("[TURN 2][INTERRUPTION] microphone input expected now")
    print("[TURN 2][INTERRUPTION] speak now: Tell me something interesting about space.")
    print("[TURN 2][INTERRUPTION] wait until JARVIS is actively speaking, then interrupt by saying: stop")
    result2 = run_voice_turn(report, personality, session=session, memory=memory)
    print(f"[TURN 2] interrupted: {result2.interrupted}")
    print(f"[TURN 2] response: {result2.response!r}")

    assert result2.interrupted, (
        "[FAIL] barge-in was not triggered during turn 2 SPEAKING phase. "
        "Re-run and speak clearly during JARVIS's spoken response."
    )
    assert result2.response is None
    assert result2.interrupted_at is not None

    turn_ids = list_session_turns(session.session_id)
    assert len(turn_ids) >= 1
    last_artifact = read_turn_artifact(session.session_id, turn_ids[-1])
    assert last_artifact.interrupted is True
    assert last_artifact.interrupted_at == result2.interrupted_at
    assert last_artifact.final_state == "INTERRUPTED"
    print(f"[ARTIFACT] interrupted=True | interrupted_at={last_artifact.interrupted_at}")

    session = SessionManager.close_session(session)
    print(f"[SESSION] closed: {session.ended_at}")
    assert session.ended_at is not None
