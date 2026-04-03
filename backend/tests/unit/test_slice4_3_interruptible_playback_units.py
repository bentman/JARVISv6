from __future__ import annotations

import threading
from pathlib import Path

import numpy as np
import pytest

from backend.app.runtimes.tts import playback


class _StreamState:
    def __init__(self, active_sequence: list[bool]) -> None:
        self._sequence = list(active_sequence)

    @property
    def active(self) -> bool:
        if self._sequence:
            return self._sequence.pop(0)
        return False


def test_play_audio_interruptible_missing_file_raises(tmp_path: Path) -> None:
    missing = tmp_path / "missing.wav"
    with pytest.raises(RuntimeError, match="file not found"):
        playback.play_audio_interruptible(str(missing), threading.Event())


def test_play_audio_interruptible_no_output_device_raises(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    audio = tmp_path / "audio.wav"
    audio.write_bytes(b"x")
    monkeypatch.setattr(playback, "has_output_device", lambda: False)
    with pytest.raises(RuntimeError, match="no output device available"):
        playback.play_audio_interruptible(str(audio), threading.Event())


def test_play_audio_interruptible_interrupts_active_playback(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    audio = tmp_path / "audio.wav"
    audio.write_bytes(b"x")

    stop_calls = {"count": 0}
    sleep_calls = {"count": 0}
    interrupt_flag = threading.Event()

    monkeypatch.setattr(playback, "has_output_device", lambda: True)
    monkeypatch.setattr(playback.sf, "read", lambda _path: (np.zeros((32, 1), dtype=np.float32), 16000))
    monkeypatch.setattr(playback.sd, "play", lambda data, rate: None)
    monkeypatch.setattr(playback.sd, "stop", lambda: stop_calls.__setitem__("count", stop_calls["count"] + 1))
    monkeypatch.setattr(playback.sd, "get_stream", lambda: _StreamState([True, True, False]))

    def _sleep(_seconds: float) -> None:
        sleep_calls["count"] += 1
        if sleep_calls["count"] == 1:
            interrupt_flag.set()

    monkeypatch.setattr(playback.time, "sleep", _sleep)

    result = playback.play_audio_interruptible(str(audio), interrupt_flag)

    assert result is False
    assert stop_calls["count"] == 1


def test_play_audio_interruptible_natural_completion_returns_true(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    audio = tmp_path / "audio.wav"
    audio.write_bytes(b"x")

    stop_calls = {"count": 0}
    interrupt_flag = threading.Event()

    monkeypatch.setattr(playback, "has_output_device", lambda: True)
    monkeypatch.setattr(playback.sf, "read", lambda _path: (np.zeros((32, 1), dtype=np.float32), 16000))
    monkeypatch.setattr(playback.sd, "play", lambda data, rate: None)
    monkeypatch.setattr(playback.sd, "stop", lambda: stop_calls.__setitem__("count", stop_calls["count"] + 1))
    monkeypatch.setattr(playback.sd, "get_stream", lambda: _StreamState([False]))
    monkeypatch.setattr(playback.time, "sleep", lambda _seconds: None)

    result = playback.play_audio_interruptible(str(audio), interrupt_flag)

    assert result is True
    assert stop_calls["count"] == 1
