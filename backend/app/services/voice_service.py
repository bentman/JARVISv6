from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
import threading

import sounddevice as sd
from backend.app.artifacts.storage import list_session_turns, read_turn_artifact, write_turn_artifact
from backend.app.conversation.engine import ConversationEngine
from backend.app.conversation.session_manager import Session
from backend.app.conversation.states import ConversationState
from backend.app.core.capabilities import FullCapabilityReport
from backend.app.memory.working import WorkingMemory
from backend.app.personality.schema import PersonalityProfile
from backend.app.runtimes.stt.barge_in import BargeInDetector
from backend.app.runtimes.stt.stt_runtime import capture_utterance, select_stt_runtime
from backend.app.runtimes.tts.playback import play_audio, play_audio_interruptible
from backend.app.runtimes.tts.tts_runtime import select_tts_runtime
from backend.app.services.turn_service import run_turn


@dataclass
class VoiceTurnResult:
    response: str | None = None
    interrupted: bool = False
    interrupted_at: str | None = None


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


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
) -> VoiceTurnResult:
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
            return VoiceTurnResult(response=response, interrupted=False, interrupted_at=None)

        tts_audio_path = str(Path(temp_dir) / "response.wav")
        tts.synthesize(response, tts_audio_path)

        interrupt_flag = threading.Event()
        detector = BargeInDetector(interrupt_flag)
        detector.start()

        if detector.failed:
            print(
                "[DEGRADED] barge-in detector unavailable "
                f"({detector.failure_reason}) — no barge-in this turn"
            )
            play_audio(tts_audio_path)
            engine.transition(ConversationState.IDLE)
            return VoiceTurnResult(response=response, interrupted=False, interrupted_at=None)

        spoken_normally = play_audio_interruptible(tts_audio_path, interrupt_flag)
        detector.stop()
        sd.stop()

        if not spoken_normally:
            interrupted_at = _now_iso()
            print(f"[INTERRUPTED] barge-in at {interrupted_at}")
            engine.transition(ConversationState.INTERRUPTED)

            if session is not None:
                turn_ids = list_session_turns(session.session_id)
                if turn_ids:
                    last_turn_id = turn_ids[-1]
                    artifact = read_turn_artifact(session.session_id, last_turn_id)
                    artifact.interrupted = True
                    artifact.interrupted_at = interrupted_at
                    artifact.final_state = ConversationState.INTERRUPTED.name
                    write_turn_artifact(artifact)

            engine.transition(ConversationState.RECOVERING)
            print("[RECOVERING] session intact — caller may invoke next turn")
            return VoiceTurnResult(response=None, interrupted=True, interrupted_at=interrupted_at)

        engine.transition(ConversationState.IDLE)
        return VoiceTurnResult(response=response, interrupted=False, interrupted_at=None)
    except Exception as exc:
        _fail("run_voice_turn", exc)
        raise
