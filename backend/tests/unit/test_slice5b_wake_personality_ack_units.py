from __future__ import annotations

import threading
import types
from pathlib import Path

import pytest

import scripts.run_jarvis as run_jarvis
from backend.app.personality import acknowledgment
from backend.app.personality.loader import load_personality_profile
from backend.app.personality.schema import PersonalityProfile
from backend.app.runtimes.wake import wakeword_runtime
from backend.app.runtimes.wake.base import WakeWordBase
from backend.app.runtimes.wake.local_runtime import PorcupineWakeWord
from backend.app.runtimes.wake.wakeword_runtime import select_wake_runtime


class _FakePorcupine:
    def __init__(self) -> None:
        self.sample_rate = 16000
        self.frame_length = 512
        self._next_result = -1
        self.deleted = False

    def process(self, _pcm: list[int]) -> int:
        return self._next_result

    def delete(self) -> None:
        self.deleted = True


class _FakeInputStream:
    def __init__(self, **kwargs) -> None:
        self.kwargs = kwargs
        self.started = False
        self.stopped = False
        self.closed = False

    def start(self) -> None:
        self.started = True

    def stop(self) -> None:
        self.stopped = True

    def close(self) -> None:
        self.closed = True


def test_is_available_false_without_access_key() -> None:
    runtime = PorcupineWakeWord(access_key="", model_path=None)
    assert runtime.is_available() is False


def test_start_sets_failed_without_access_key() -> None:
    runtime = PorcupineWakeWord(access_key="", model_path=None)
    wake_flag = threading.Event()

    runtime.start(wake_flag)

    assert runtime.failed is True
    assert runtime.failure_reason == "PICOVOICE_ACCESS_KEY is not set"


def test_start_stop_and_detection_sets_wake_flag(monkeypatch, tmp_path) -> None:
    fake_porcupine = _FakePorcupine()
    fake_stream: _FakeInputStream | None = None

    def _create(**_kwargs):
        return fake_porcupine

    def _input_stream(**kwargs):
        nonlocal fake_stream
        fake_stream = _FakeInputStream(**kwargs)
        return fake_stream

    fake_pvporcupine = types.SimpleNamespace(create=_create)
    fake_sd = types.SimpleNamespace(InputStream=_input_stream)

    monkeypatch.setitem(__import__("sys").modules, "pvporcupine", fake_pvporcupine)
    monkeypatch.setitem(__import__("sys").modules, "sounddevice", fake_sd)

    model_path = tmp_path / "wake.ppn"
    model_path.write_text("stub", encoding="utf-8")
    runtime = PorcupineWakeWord(access_key="key", model_path=str(model_path))
    wake_flag = threading.Event()

    runtime.start(wake_flag)
    assert runtime.failed is False
    assert fake_stream is not None
    assert fake_stream.started is True

    fake_porcupine._next_result = 0
    callback = fake_stream.kwargs["callback"]
    callback([[0], [0]], 2, None, None)
    assert wake_flag.is_set() is True

    runtime.stop()
    assert fake_stream.stopped is True
    assert fake_stream.closed is True
    assert fake_porcupine.deleted is True


def test_select_wake_runtime_uses_settings_and_returns_none_when_unavailable(monkeypatch) -> None:
    monkeypatch.setattr(wakeword_runtime.settings, "PICOVOICE_ACCESS_KEY", None)
    monkeypatch.setattr(wakeword_runtime.settings, "PVPORCUPINE_MODEL_PATH", None)

    selected = wakeword_runtime.select_wake_runtime()

    assert selected is None


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


def test_wake_word_base_is_abstract() -> None:
    with pytest.raises(TypeError):
        WakeWordBase()


def test_presence_surfaces_are_importable_and_callable() -> None:
    assert callable(select_wake_runtime)
    assert callable(acknowledgment.generate_acknowledgment)
    assert callable(acknowledgment.play_acknowledgment_if_configured)
    assert callable(run_jarvis.main)


def test_personality_profile_additive_fields_present_in_loaded_default() -> None:
    profile = load_personality_profile("default")

    assert isinstance(profile, PersonalityProfile)
    assert hasattr(profile, "acknowledgment_phrase_style")
    assert hasattr(profile, "wake_response_sound")


def test_wake_runtime_selector_returns_none_without_key() -> None:
    selected = select_wake_runtime(access_key="", model_path=None)
    assert selected is None


def test_wake_runtime_stop_does_not_call_sd_stop(monkeypatch, tmp_path) -> None:
    class _FakePorcupine:
        sample_rate = 16000
        frame_length = 512

        def process(self, _pcm) -> int:
            return -1

        def delete(self) -> None:
            return None

    class _FakeInputStream:
        def __init__(self, **_kwargs) -> None:
            self.started = False
            self.stopped = False
            self.closed = False

        def start(self) -> None:
            self.started = True

        def stop(self) -> None:
            self.stopped = True

        def close(self) -> None:
            self.closed = True

    def _create(**_kwargs):
        return _FakePorcupine()

    def _input_stream(**kwargs):
        return _FakeInputStream(**kwargs)

    def _fail_stop() -> None:
        raise AssertionError("sd.stop() should not be called by PorcupineWakeWord.stop()")

    fake_pvporcupine = types.SimpleNamespace(create=_create)
    fake_sd = types.SimpleNamespace(InputStream=_input_stream, stop=_fail_stop)

    monkeypatch.setitem(__import__("sys").modules, "pvporcupine", fake_pvporcupine)
    monkeypatch.setitem(__import__("sys").modules, "sounddevice", fake_sd)

    ppn_path = tmp_path / "wake.ppn"
    ppn_path.write_text("stub", encoding="utf-8")

    runtime = PorcupineWakeWord(access_key="key", model_path=str(ppn_path))
    runtime.start(threading.Event())
    runtime.stop()