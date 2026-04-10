from __future__ import annotations

import threading
import types

import pytest

import scripts.run_jarvis as run_jarvis
from backend.app.personality import acknowledgment
from backend.app.personality.loader import load_personality_profile
from backend.app.personality.schema import PersonalityProfile
from backend.app.runtimes.wake.base import WakeWordBase
from backend.app.runtimes.wake.local_runtime import PorcupineWakeWord
from backend.app.runtimes.wake.wakeword_runtime import select_wake_runtime


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
