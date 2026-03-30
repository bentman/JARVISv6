from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True)
class PersonalityProfile:
    profile_id: str
    display_name: str
    identity_summary: str
    tone: str
    brevity: str
    formality: str
    warmth: str
    assertiveness: str
    humor_policy: str
    response_style: str
    acknowledgment_style: str
    interruption_style: str
    voice_pacing: str
    voice_energy: str
    safety_overrides: list[str]
    enabled: bool
