from __future__ import annotations

from dataclasses import dataclass


@dataclass
class TurnArtifact:
    turn_id: str
    session_id: str
    turn_index: int
    input_modality: str
    transcript: str
    prompt_text: str
    response_text: str
    personality_profile_id: str
    stt_model: str | None
    llm_runtime: str
    tts_runtime: str | None
    final_state: str
    failure_reason: str | None
    started_at: str
    responded_at: str
    completed_at: str