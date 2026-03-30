from __future__ import annotations

from enum import Enum


class ConversationState(str, Enum):
    BOOTSTRAP = "BOOTSTRAP"
    PROFILING = "PROFILING"
    IDLE = "IDLE"
    LISTENING = "LISTENING"
    TRANSCRIBING = "TRANSCRIBING"
    REASONING = "REASONING"
    ACTING = "ACTING"
    RESPONDING = "RESPONDING"
    SPEAKING = "SPEAKING"
    INTERRUPTED = "INTERRUPTED"
    RECOVERING = "RECOVERING"
    FAILED = "FAILED"
