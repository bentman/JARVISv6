from __future__ import annotations

from pathlib import Path

from backend.app.cognition.prompt_assembler import assemble_prompt
from backend.app.cognition.responder import get_response
from backend.app.conversation.engine import ConversationEngine
from backend.app.conversation.states import ConversationState
from backend.app.core.capabilities import FullCapabilityReport
from backend.app.personality.schema import PersonalityProfile
from backend.app.routing.runtime_selector import select_llm_runtime
from backend.app.runtimes.stt.local_runtime import FasterWhisperSTT
from backend.app.runtimes.stt.stt_runtime import capture_utterance


def ensure_temp_dir() -> str:
    path = Path("data") / "temp"
    path.mkdir(parents=True, exist_ok=True)
    return str(path)


def run_voice_turn(report: FullCapabilityReport, personality: PersonalityProfile) -> str:
    engine = ConversationEngine(report, personality)

    def _fail(step_name: str, exc: Exception) -> None:
        try:
            if engine.state != ConversationState.FAILED:
                engine.transition(ConversationState.FAILED)
        finally:
            print(f"[FAILED] {step_name}: {exc}")

    try:
        engine.transition(ConversationState.LISTENING)

        temp_dir = ensure_temp_dir()
        audio_path = capture_utterance(
            output_path=str(Path(temp_dir) / "utterance.wav"),
            duration_seconds=5,
        )

        engine.transition(ConversationState.TRANSCRIBING)
        stt = FasterWhisperSTT(
            report.flags.stt_recommended_model,
            device="cuda" if report.profile.cuda_available else "cpu",
        )
        transcript = stt.transcribe(audio_path)
        print(f"[TRANSCRIPT] {transcript}")

        engine.transition(ConversationState.REASONING)
        llm = select_llm_runtime()
        print(f"[LLM RUNTIME] {type(llm).__name__}")

        prompt = assemble_prompt(transcript, personality)

        engine.transition(ConversationState.RESPONDING)
        response = get_response(prompt, llm)
        print(f"[RESPONSE] {response}")

        engine.transition(ConversationState.IDLE)
        return response
    except Exception as exc:
        _fail("run_voice_turn", exc)
        raise
