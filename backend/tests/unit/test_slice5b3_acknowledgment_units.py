from __future__ import annotations

from pathlib import Path

from backend.app.personality import acknowledgment
from backend.app.personality.schema import PersonalityProfile


def _personality(style: str) -> PersonalityProfile:
    return PersonalityProfile(
        profile_id="default",
        display_name="JARVIS",
        identity_summary="A direct, capable local assistant.",
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
        acknowledgment_phrase_style=style,
    )


def test_generate_acknowledgment_minimal_returns_none() -> None:
    assert acknowledgment.generate_acknowledgment(_personality("minimal")) is None


def test_generate_acknowledgment_standard_is_deterministic_and_non_empty() -> None:
    first = acknowledgment.generate_acknowledgment(_personality("standard"))
    second = acknowledgment.generate_acknowledgment(_personality("standard"))

    assert isinstance(first, str)
    assert bool(first.strip())
    assert first == second


def test_generate_acknowledgment_warm_is_deterministic_and_non_empty() -> None:
    first = acknowledgment.generate_acknowledgment(_personality("warm"))
    second = acknowledgment.generate_acknowledgment(_personality("warm"))

    assert isinstance(first, str)
    assert bool(first.strip())
    assert first == second


def test_play_acknowledgment_noop_for_minimal(monkeypatch, tmp_path: Path) -> None:
    class _FakeTTS:
        called = False

        def synthesize(self, text: str, output_path: str) -> str:
            self.called = True
            return output_path

    fake_tts = _FakeTTS()
    monkeypatch.setattr(acknowledgment, "play_audio", lambda _path: (_ for _ in ()).throw(AssertionError("play_audio should not be called")))

    acknowledgment.play_acknowledgment_if_configured(_personality("minimal"), fake_tts, str(tmp_path))

    assert fake_tts.called is False


def test_play_acknowledgment_noop_for_tts_none(monkeypatch, tmp_path: Path) -> None:
    called = {"play": False}
    monkeypatch.setattr(acknowledgment, "play_audio", lambda _path: called.__setitem__("play", True))

    acknowledgment.play_acknowledgment_if_configured(_personality("standard"), None, str(tmp_path))

    assert called["play"] is False


def test_play_acknowledgment_swallows_synthesis_failure_and_logs_degraded(
    capsys,
    tmp_path: Path,
) -> None:
    class _FailingTTS:
        def synthesize(self, text: str, output_path: str) -> str:
            raise RuntimeError("tts boom")

    acknowledgment.play_acknowledgment_if_configured(
        _personality("standard"),
        _FailingTTS(),
        str(tmp_path),
    )
    output = capsys.readouterr().out
    assert "[DEGRADED] acknowledgment skipped:" in output
