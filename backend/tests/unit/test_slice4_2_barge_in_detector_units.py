from __future__ import annotations

import threading

import numpy as np

from backend.app.runtimes.stt import barge_in
from backend.app.runtimes.stt.barge_in import BargeInDetector


class _FakeStream:
    def __init__(self, callback) -> None:
        self.callback = callback
        self.started = False
        self.stopped = False
        self.closed = False

    def start(self) -> None:
        self.started = True

    def stop(self) -> None:
        self.stopped = True

    def close(self) -> None:
        self.closed = True


def test_barge_in_detector_sets_flag_on_threshold(monkeypatch) -> None:
    holder: dict[str, _FakeStream] = {}

    def _input_stream_factory(*, callback, **kwargs):
        stream = _FakeStream(callback)
        holder["stream"] = stream
        return stream

    monkeypatch.setattr(barge_in.sd, "InputStream", _input_stream_factory)

    flag = threading.Event()
    detector = BargeInDetector(flag, threshold=0.02, min_trigger_frames=2)
    detector.start()

    assert holder["stream"].started is True
    low_energy = np.zeros((1024, 1), dtype=np.float32)
    high_energy = np.full((1024, 1), 0.1, dtype=np.float32)

    holder["stream"].callback(low_energy, 1024, None, None)
    assert flag.is_set() is False
    holder["stream"].callback(high_energy, 1024, None, None)
    assert flag.is_set() is False
    holder["stream"].callback(high_energy, 1024, None, None)
    assert flag.is_set() is True


def test_barge_in_detector_no_flag_below_threshold(monkeypatch) -> None:
    holder: dict[str, _FakeStream] = {}

    def _input_stream_factory(*, callback, **kwargs):
        stream = _FakeStream(callback)
        holder["stream"] = stream
        return stream

    monkeypatch.setattr(barge_in.sd, "InputStream", _input_stream_factory)

    flag = threading.Event()
    detector = BargeInDetector(flag, threshold=0.5, min_trigger_frames=2)
    detector.start()

    below_threshold = np.full((1024, 1), 0.01, dtype=np.float32)
    holder["stream"].callback(below_threshold, 1024, None, None)
    holder["stream"].callback(below_threshold, 1024, None, None)
    holder["stream"].callback(below_threshold, 1024, None, None)
    assert flag.is_set() is False


def test_barge_in_detector_failed_on_stream_open_error(monkeypatch) -> None:
    def _input_stream_factory(**kwargs):
        raise OSError("input unavailable")

    monkeypatch.setattr(barge_in.sd, "InputStream", _input_stream_factory)

    flag = threading.Event()
    detector = BargeInDetector(flag)
    detector.start()

    assert detector.failed is True
    assert detector.failure_reason is not None
    assert "input unavailable" in detector.failure_reason
    assert flag.is_set() is False


def test_barge_in_detector_stop_does_not_call_sd_stop(monkeypatch) -> None:
    holder: dict[str, _FakeStream] = {}
    sd_stop_called = {"called": False}

    def _input_stream_factory(*, callback, **kwargs):
        stream = _FakeStream(callback)
        holder["stream"] = stream
        return stream

    def _sd_stop() -> None:
        sd_stop_called["called"] = True

    monkeypatch.setattr(barge_in.sd, "InputStream", _input_stream_factory)
    monkeypatch.setattr(barge_in.sd, "stop", _sd_stop)

    flag = threading.Event()
    detector = BargeInDetector(flag)
    detector.start()
    detector.stop()

    assert holder["stream"].stopped is True
    assert holder["stream"].closed is True
    assert sd_stop_called["called"] is False
