from __future__ import annotations

from pathlib import Path

import yaml

from backend.app.personality.schema import PersonalityProfile


REQUIRED_FIELDS = [
    "profile_id",
    "display_name",
    "identity_summary",
    "tone",
    "brevity",
    "formality",
    "warmth",
    "assertiveness",
    "humor_policy",
    "response_style",
    "acknowledgment_style",
    "interruption_style",
    "voice_pacing",
    "voice_energy",
    "safety_overrides",
    "enabled",
]


def load_personality_profile(name: str = "default") -> PersonalityProfile:
    profile_path = Path("config") / "personality" / f"{name}.yaml"
    if not profile_path.exists():
        raise FileNotFoundError(f"Personality profile file not found: {profile_path}")

    raw = yaml.safe_load(profile_path.read_text(encoding="utf-8"))
    data = raw if isinstance(raw, dict) else {}

    missing = [field for field in REQUIRED_FIELDS if field not in data]
    if missing:
        raise ValueError(
            f"Personality profile missing required fields: {missing} (file: {profile_path})"
        )

    return PersonalityProfile(
        profile_id=str(data["profile_id"]),
        display_name=str(data["display_name"]),
        identity_summary=str(data["identity_summary"]),
        tone=str(data["tone"]),
        brevity=str(data["brevity"]),
        formality=str(data["formality"]),
        warmth=str(data["warmth"]),
        assertiveness=str(data["assertiveness"]),
        humor_policy=str(data["humor_policy"]),
        response_style=str(data["response_style"]),
        acknowledgment_style=str(data["acknowledgment_style"]),
        interruption_style=str(data["interruption_style"]),
        voice_pacing=str(data["voice_pacing"]),
        voice_energy=str(data["voice_energy"]),
        safety_overrides=list(data["safety_overrides"]),
        enabled=bool(data["enabled"]),
    )
