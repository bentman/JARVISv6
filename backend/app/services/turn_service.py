from __future__ import annotations

from datetime import datetime, timezone
from uuid import uuid4

from backend.app.artifacts.storage import write_turn_artifact
from backend.app.artifacts.turn_artifact import TurnArtifact
from backend.app.cognition.prompt_assembler import assemble_prompt
from backend.app.cognition.responder import enforce_identity_response, get_response
from backend.app.conversation.engine import ConversationEngine
from backend.app.conversation.session_manager import Session, SessionManager
from backend.app.conversation.states import ConversationState
from backend.app.core.capabilities import FullCapabilityReport
from backend.app.memory.working import TurnSummary, WorkingMemory
from backend.app.memory.write_policy import evaluate_write_policy
from backend.app.personality.schema import PersonalityProfile
from backend.app.routing.runtime_selector import select_llm_runtime


def _iso_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def run_turn(
    report: FullCapabilityReport,
    personality: PersonalityProfile,
    transcript: str,
    *,
    session: Session | None = None,
    memory: WorkingMemory | None = None,
    input_modality: str = "text",
) -> str:
    engine = ConversationEngine(report, personality)

    started_at = _iso_now()
    responded_at = started_at
    completed_at = started_at
    failure_reason: str | None = None

    try:
        engine.transition(ConversationState.REASONING)
        llm = select_llm_runtime()

        context_turns = memory.get_context_turns() if memory is not None else None
        prompt = assemble_prompt(
            transcript,
            personality,
            context_turns=context_turns,
        )

        engine.transition(ConversationState.RESPONDING)
        response = get_response(prompt, llm)
        response = enforce_identity_response(transcript, response, personality)

        responded_at = _iso_now()

        engine.transition(ConversationState.IDLE)
        decision = evaluate_write_policy(transcript, response, engine.state.name)
        print(f"[MEMORY] {decision.reason}")

        if decision.should_write and memory is not None:
            turn_index = session.turn_count if session is not None else len(memory.get_context_turns())
            memory.add_turn(
                TurnSummary(
                    turn_index=turn_index,
                    transcript=transcript,
                    response_text=response,
                )
            )

        if session is not None:
            turn_index = session.turn_count
            completed_at = _iso_now()
            artifact = TurnArtifact(
                turn_id=str(uuid4()),
                session_id=session.session_id,
                turn_index=turn_index,
                input_modality=input_modality,
                transcript=transcript,
                prompt_text=prompt,
                response_text=response,
                personality_profile_id=personality.profile_id,
                stt_model=None,
                llm_runtime=type(llm).__name__,
                tts_runtime=None,
                final_state=engine.state.name,
                failure_reason=None,
                started_at=started_at,
                responded_at=responded_at,
                completed_at=completed_at,
            )
            write_turn_artifact(artifact)
            SessionManager.increment_turn(session)

        return response
    except Exception as exc:
        failure_reason = str(exc)
        if engine.state != ConversationState.FAILED:
            try:
                engine.transition(ConversationState.FAILED)
            except Exception:
                pass
        print(f"[FAILED] run_turn: {failure_reason}")
        raise