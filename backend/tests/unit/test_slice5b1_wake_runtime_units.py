from __future__ import annotations

import threading
import types

from backend.app.runtimes.wake.local_runtime import PorcupineWakeWord
from backend.app.runtimes.wake import wakeword_runtime


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
