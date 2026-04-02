from __future__ import annotations

import re

from backend.app.runtimes.llm.base import LLMBase


_DIVIDER_RE = re.compile(r"^\s*---+\s*$")
_TEXT_COMPLETION_RE = re.compile(r"^\s*#{1,6}\s*Text completion\b", re.IGNORECASE)
_SYSTEM_CONTEXT_RE = re.compile(r"^\s*System context\s*:?(?:\s+.*)?$", re.IGNORECASE)
_IDENTITY_SUMMARY_RE = re.compile(r"\bidentity_summary\s*:", re.IGNORECASE)
_TONE_LINE_RE = re.compile(r"^\s*-\s*tone\s*:", re.IGNORECASE)
_USER_TURN_RE = re.compile(r"^\s*User turn\s*:\s*(.*)$", re.IGNORECASE)
_ASSISTANT_TAG_RE = re.compile(r"^\s*(assistant|response|reply|answer)\s*:\s*(.*)$", re.IGNORECASE)

# Continuation-bleed markers: model invented the next user turn or a turn separator.
# These truncate the response — everything from the marker onward is discarded.
_CONTINUATION_BLEED_RE = re.compile(
    r"^\s*(?:"
    r"User\s*:"           # bare "User:" prefix
    r"|Human\s*:"         # bare "Human:" prefix
    r"|\[New turn[:\]]"   # "[New turn:]" or "[New turn]"
    r"|\[Turn \d+"        # "[Turn N]" fabricated turn markers
    r")",
    re.IGNORECASE,
)


def _sanitize_response(raw_response: str) -> str:
    lines = raw_response.replace("\r\n", "\n").replace("\r", "\n").split("\n")
    cleaned: list[str] = []
    in_system_context = False
    in_user_turn = False

    for line in lines:
        stripped = line.strip()

        if _DIVIDER_RE.match(stripped) or _TEXT_COMPLETION_RE.match(stripped):
            continue

        if _SYSTEM_CONTEXT_RE.match(stripped):
            in_system_context = True
            continue

        user_turn_match = _USER_TURN_RE.match(stripped)
        if user_turn_match:
            in_system_context = False
            in_user_turn = True
            continue

        if in_system_context:
            if not stripped:
                in_system_context = False
            continue

        if in_user_turn:
            assistant_match = _ASSISTANT_TAG_RE.match(stripped)
            if assistant_match:
                in_user_turn = False
                assistant_content = assistant_match.group(2).strip()
                if assistant_content:
                    cleaned.append(assistant_content)
                continue
            if not stripped:
                in_user_turn = False
            continue

        if _IDENTITY_SUMMARY_RE.search(stripped):
            continue
        if _TONE_LINE_RE.match(stripped):
            continue
        if re.search(r"\bSystem context\b", stripped, flags=re.IGNORECASE):
            continue
        if re.search(r"\bText completion\b", stripped, flags=re.IGNORECASE):
            continue

        # Defense-in-depth: truncate if the model bleeds into a fabricated next turn.
        # Only applies after at least one response line has been collected so we do
        # not accidentally truncate a legitimately short first line.
        if cleaned and _CONTINUATION_BLEED_RE.match(stripped):
            break

        cleaned.append(line)

    sanitized = "\n".join(cleaned).strip()
    return sanitized


def get_response(prompt: str, llm: LLMBase) -> str:
    response = llm.complete(prompt)
    if not response or not response.strip():
        raise RuntimeError("responder: empty response from LLM")
    sanitized = _sanitize_response(response)
    if not sanitized:
        raise RuntimeError("responder: sanitized response is empty after removing prompt scaffolding")
    return sanitized
