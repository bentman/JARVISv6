from __future__ import annotations

import json
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
    "acknowledgment_phrase_style",
    "wake_response_sound",
    "interruption_style",
    "voice_pacing",
    "voice_energy",
    "safety_overrides",
    "enabled",
]


def _load_json_identity_base() -> dict[str, object]:
    json_path = Path("config") / "personality" / "jarvis_personality.json"
    if not json_path.exists():
        raise FileNotFoundError(f"Personality identity base file not found: {json_path}")

    raw = json.loads(json_path.read_text(encoding="utf-8"))
    if not isinstance(raw, dict):
        raise ValueError(f"Personality identity base is not a JSON object: {json_path}")

    identity = raw.get("identity")
    persona = raw.get("personality")
    if not isinstance(identity, dict):
        raise ValueError(f"Personality identity base missing object: identity (file: {json_path})")
    if not isinstance(persona, dict):
        raise ValueError(f"Personality identity base missing object: personality (file: {json_path})")

    name = str(identity.get("name", "")).strip()
    display_name = str(identity.get("display_name", "")).strip()
    full_name = str(identity.get("full_name", "")).strip()
    role = str(identity.get("role", "")).strip()

    if not name or not display_name or not role:
        raise ValueError(
            "Personality identity base missing required identity fields: "
            "name/display_name/role"
        )

    traits_raw = persona.get("traits")
    traits = [str(t).strip() for t in traits_raw] if isinstance(traits_raw, list) else []
    trait_text = ", ".join([t for t in traits if t]) if traits else "configured"

    identity_summary = (
        f"You are {display_name} ({full_name or name}), the user's {role}. "
        f"Maintain this exact identity and do not claim to be any other assistant or model. "
        f"Core persona traits: {trait_text}."
    )

    base_tone = str(persona.get("tone", "")).strip() or "professional"

    return {
        "display_name": display_name,
        "identity_summary": identity_summary,
        "tone": base_tone,
    }


def load_personality_profile(name: str = "default") -> PersonalityProfile:
    identity_base = _load_json_identity_base()

    profile_path = Path("config") / "personality" / f"{name}.yaml"
    if not profile_path.exists():
        raise FileNotFoundError(f"Personality profile file not found: {profile_path}")

    raw = yaml.safe_load(profile_path.read_text(encoding="utf-8"))
    yaml_data = raw if isinstance(raw, dict) else {}

    data = dict(yaml_data)
    # Identity/persona authority is JSON-first and not overridden by YAML.
    data["display_name"] = identity_base["display_name"]
    data["identity_summary"] = identity_base["identity_summary"]
    if "tone" not in data:
        data["tone"] = identity_base["tone"]
    data.setdefault("acknowledgment_phrase_style", "minimal")
    data.setdefault("wake_response_sound", "none")

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
        acknowledgment_phrase_style=str(data["acknowledgment_phrase_style"]),
        wake_response_sound=str(data["wake_response_sound"]),
        interruption_style=str(data["interruption_style"]),
        voice_pacing=str(data["voice_pacing"]),
        voice_energy=str(data["voice_energy"]),
        safety_overrides=list(data["safety_overrides"]),
        enabled=bool(data["enabled"]),
    )
