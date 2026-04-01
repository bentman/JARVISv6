from __future__ import annotations

from typing import TYPE_CHECKING

from backend.app.personality.schema import PersonalityProfile

if TYPE_CHECKING:
    from backend.app.memory.working import TurnSummary


def assemble_prompt(
    transcript: str,
    personality: PersonalityProfile,
    context_turns: list[TurnSummary] | None = None,
) -> str:
    if context_turns:
        prior_lines: list[str] = []
        for turn in context_turns:
            prior_lines.append(f"User: {turn.transcript}")
            prior_lines.append(f"Assistant: {turn.response_text}")

        prior_block = "\n".join(prior_lines)
        return (
            f"[System: {personality.identity_summary}. Tone: {personality.tone}.]\n\n"
            "[Prior turns:]\n"
            f"{prior_block}\n\n"
            f"User: {transcript}"
        )

    return (
        "System context:\n"
        f"- identity_summary: {personality.identity_summary}\n"
        f"- tone: {personality.tone}\n\n"
        "User turn:\n"
        f"{transcript}"
    )
