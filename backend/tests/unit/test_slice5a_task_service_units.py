from __future__ import annotations

from typing import Any

from backend.app.services import task_service


def test_run_text_turn_success_path(monkeypatch) -> None:
    monkeypatch.setattr(task_service, "run_turn", lambda *args, **kwargs: "ok")

    report: Any = object()
    personality: Any = object()

    result = task_service.run_text_turn(
        "hello",
        report=report,
        personality=personality,
    )

    assert result.response == "ok"
    assert result.failed is False
    assert result.failure_reason is None


def test_run_text_turn_failure_path(monkeypatch) -> None:
    def _raise(*args, **kwargs):
        raise RuntimeError("boom")

    monkeypatch.setattr(task_service, "run_turn", _raise)

    report: Any = object()
    personality: Any = object()

    result = task_service.run_text_turn(
        "hello",
        report=report,
        personality=personality,
    )

    assert result.response == ""
    assert result.failed is True
    assert result.failure_reason == "boom"


def test_run_text_turn_forwards_session_memory_and_text_modality(monkeypatch) -> None:
    captured: dict[str, object] = {}

    def _fake_run_turn(report, personality, transcript, *, session=None, memory=None, input_modality="text"):
        captured["report"] = report
        captured["personality"] = personality
        captured["transcript"] = transcript
        captured["session"] = session
        captured["memory"] = memory
        captured["input_modality"] = input_modality
        return "forwarded"

    monkeypatch.setattr(task_service, "run_turn", _fake_run_turn)

    report: Any = object()
    personality: Any = object()
    session: Any = object()
    memory: Any = object()

    result = task_service.run_text_turn(
        "typed input",
        report=report,
        personality=personality,
        session=session,
        memory=memory,
    )

    assert result.response == "forwarded"
    assert result.failed is False
    assert captured["report"] is report
    assert captured["personality"] is personality
    assert captured["transcript"] == "typed input"
    assert captured["session"] is session
    assert captured["memory"] is memory
    assert captured["input_modality"] == "text"
