from __future__ import annotations

from dataclasses import dataclass


@dataclass
class WriteDecision:
    should_write: bool
    reason: str


def evaluate_write_policy(
    transcript: str,
    response_text: str,
    final_state: str,
) -> WriteDecision:
    if final_state == "FAILED":
        return WriteDecision(
            should_write=False,
            reason="turn failed — not written to working memory",
        )

    if transcript.strip() == "":
        return WriteDecision(
            should_write=False,
            reason="empty transcript — not written to working memory",
        )

    if response_text.strip() == "":
        return WriteDecision(
            should_write=False,
            reason="empty response — not written to working memory",
        )

    return WriteDecision(
        should_write=True,
        reason="turn complete — written to working memory",
    )