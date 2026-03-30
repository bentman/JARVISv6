from __future__ import annotations

from backend.app.personality.schema import PersonalityProfile


def assemble_prompt(transcript: str, personality: PersonalityProfile) -> str:
    return (
        "System context:\n"
        f"- identity_summary: {personality.identity_summary}\n"
        f"- tone: {personality.tone}\n\n"
        "User turn:\n"
        f"{transcript}"
    )
