from __future__ import annotations

from backend.app.personality.loader import load_personality_profile
from backend.app.personality.schema import PersonalityProfile


def _profile_with_required_fields() -> PersonalityProfile:
    return PersonalityProfile(
        profile_id="default",
        display_name="Jarvis",
        identity_summary="Identity summary",
        tone="neutral",
        brevity="concise",
        formality="professional",
        warmth="measured",
        assertiveness="moderate",
        humor_policy="none",
        response_style="direct",
        acknowledgment_style="minimal",
        interruption_style="stop-and-listen",
        voice_pacing="moderate",
        voice_energy="calm",
        safety_overrides=[],
        enabled=True,
    )


def test_personality_profile_new_fields_default_values() -> None:
    profile = _profile_with_required_fields()

    assert profile.acknowledgment_phrase_style == "minimal"
    assert profile.wake_response_sound == "none"


def test_default_profile_loads_and_applies_new_field_defaults() -> None:
    profile = load_personality_profile("default")

    assert isinstance(profile, PersonalityProfile)
    assert profile.profile_id == "default"
    assert profile.acknowledgment_phrase_style == "minimal"
    assert profile.wake_response_sound == "none"
