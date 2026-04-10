from __future__ import annotations

import hashlib
from pathlib import Path

from backend.app.personality.schema import PersonalityProfile
from backend.app.runtimes.tts.base import TTSBase
from backend.app.runtimes.tts.playback import play_audio


def _stable_index(profile_id: str, size: int) -> int:
    if size <= 0:
        raise ValueError("size must be positive")
    digest = hashlib.sha256(profile_id.encode("utf-8")).hexdigest()
    return int(digest, 16) % size


def generate_acknowledgment(personality: PersonalityProfile) -> str | None:
    style = (personality.acknowledgment_phrase_style or "minimal").strip().lower()
    if style == "minimal":
        return None

    if style == "standard":
        phrases = ("Got it.", "Sure.", "One moment.")
    elif style == "warm":
        phrases = ("Of course.", "Absolutely.", "Right away.")
    else:
        return None

    return phrases[_stable_index(personality.profile_id, len(phrases))]


def play_acknowledgment_if_configured(
    personality: PersonalityProfile,
    tts: TTSBase | None,
    temp_dir: str,
) -> None:
    phrase = generate_acknowledgment(personality)
    if phrase is None:
        return
    if tts is None:
        return

    try:
        audio_path = str(Path(temp_dir) / "acknowledgment.wav")
        tts.synthesize(phrase, audio_path)
        play_audio(audio_path)
    except Exception as exc:
        print(f"[DEGRADED] acknowledgment skipped: {exc}")
