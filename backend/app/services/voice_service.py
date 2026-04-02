from __future__ import annotations

from pathlib import Path

from backend.app.conversation.engine import ConversationEngine
from backend.app.conversation.session_manager import Session
from backend.app.conversation.states import ConversationState
from backend.app.core.capabilities import FullCapabilityReport
from backend.app.memory.working import WorkingMemory
from backend.app.personality.schema import PersonalityProfile
from backend.app.runtimes.stt.stt_runtime import capture_utterance, select_stt_runtime
from backend.app.runtimes.tts.playback import play_audio
from backend.app.runtimes.tts.tts_runtime import select_tts_runtime
from backend.app.services.turn_service import run_turn


def ensure_temp_dir() -> str:
    path = Path("data") / "temp"
    path.mkdir(parents=True, exist_ok=True)
    return str(path)


def run_voice_turn(
    report: FullCapabilityReport,
    personality: PersonalityProfile,
    *,
    session: Session | None = None,
    memory: WorkingMemory | None = None,
) -> str:
    engine = ConversationEngine(report, personality)

    def _fail(step_name: str, exc: Exception) -> None:
        try:
            if engine.state != ConversationState.FAILED:
                engine.transition(ConversationState.FAILED)
        finally:
            print(f"[FAILED] {step_name}: {exc}")

    try:
        engine.transition(ConversationState.LISTENING)
        print("[LIVE INPUT] awaiting microphone speech...")

        temp_dir = ensure_temp_dir()
        audio_path = capture_utterance(
            output_path=str(Path(temp_dir) / "utterance.wav"),
            duration_seconds=5,
        )

        engine.transition(ConversationState.TRANSCRIBING)
        stt = select_stt_runtime(report)
        if stt is None:
            raise RuntimeError("run_voice_turn: no STT runtime available")
        transcript = stt.transcribe(audio_path)
        print(f"[TRANSCRIPT] {transcript}")

        response = run_turn(
            report,
            personality,
            transcript,
            session=session,
            memory=memory,
            input_modality="voice",
        )
        print(f"[RESPONSE] {response}")

        engine.transition(ConversationState.SPEAKING)
        tts = select_tts_runtime(report)
        if tts is None:
            print("[DEGRADED] TTS unavailable — text response only")
            engine.transition(ConversationState.IDLE)
            return response

        tts_audio_path = str(Path(temp_dir) / "response.wav")
        tts.synthesize(response, tts_audio_path)
        play_audio(tts_audio_path)

        engine.transition(ConversationState.IDLE)
        return response
    except Exception as exc:
        _fail("run_voice_turn", exc)
        raise
