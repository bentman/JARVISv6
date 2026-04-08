from __future__ import annotations

from dataclasses import dataclass

from backend.app.conversation.session_manager import Session
from backend.app.core.capabilities import FullCapabilityReport
from backend.app.memory.working import WorkingMemory
from backend.app.personality.schema import PersonalityProfile
from backend.app.services.turn_service import run_turn


@dataclass(slots=True)
class TextTurnResult:
    response: str
    failed: bool = False
    failure_reason: str | None = None


def run_text_turn(
    text: str,
    report: FullCapabilityReport,
    personality: PersonalityProfile,
    *,
    session: Session | None = None,
    memory: WorkingMemory | None = None,
) -> TextTurnResult:
    """Run a typed turn through the shared turn engine and wrap result state."""

    try:
        response = run_turn(
            report,
            personality,
            text,
            session=session,
            memory=memory,
            input_modality="text",
        )
        return TextTurnResult(response=response)
    except Exception as exc:
        return TextTurnResult(response="", failed=True, failure_reason=str(exc))
