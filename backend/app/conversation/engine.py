from __future__ import annotations

from backend.app.conversation.states import ConversationState
from backend.app.core.capabilities import FullCapabilityReport
from backend.app.personality.schema import PersonalityProfile


_ALLOWED_FROM: dict[ConversationState, set[ConversationState]] = {
    ConversationState.INTERRUPTED: {ConversationState.RECOVERING},
    ConversationState.RECOVERING: {ConversationState.LISTENING, ConversationState.FAILED},
}


class ConversationEngine:
    def __init__(self, report: FullCapabilityReport, personality: PersonalityProfile) -> None:
        self.report = report
        self.personality = personality
        self.state: ConversationState = ConversationState.IDLE

    def transition(self, new_state: ConversationState) -> None:
        if self.state == new_state:
            raise RuntimeError(f"ConversationEngine: no-op transition to {new_state.name}")
        allowed_states = _ALLOWED_FROM.get(self.state)
        if allowed_states is not None and new_state not in allowed_states:
            raise RuntimeError(
                f"ConversationEngine: illegal transition {self.state.name} → {new_state.name}"
            )
        previous = self.state
        self.state = new_state
        print(f"[STATE] {previous.name} → {new_state.name}")
