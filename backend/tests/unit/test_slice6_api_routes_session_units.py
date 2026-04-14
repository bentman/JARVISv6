from __future__ import annotations

import threading
import time
from types import SimpleNamespace
from typing import Any, cast

from fastapi.testclient import TestClient

from backend.app.api import main as api_main
from backend.app.api.routes import health as health_routes
from backend.app.api.routes import session as session_routes
from backend.app.services import session_service
from backend.app.services.startup_service import StartupSummary
from backend.app.services.voice_service import VoiceTurnResult


def _startup_context() -> SimpleNamespace:
    return SimpleNamespace(
        summary=SimpleNamespace(
            profile_id="test-profile",
            stt_ready=True,
            tts_ready=True,
            llm_ready=True,
        ),
        report=object(),
        personality=object(),
    )


def test_health_route_returns_required_readiness_fields(monkeypatch) -> None:
    monkeypatch.setattr(health_routes, "get_startup_error", lambda: None)
    monkeypatch.setattr(health_routes, "is_startup_context_ready", lambda: True)
    monkeypatch.setattr(health_routes, "get_startup_context_if_ready", _startup_context)

    client = TestClient(api_main.app)
    response = client.get("/health")

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "ok"
    assert payload["profile_id"] == "test-profile"
    assert payload["stt_ready"] is True
    assert payload["tts_ready"] is True
    assert payload["llm_ready"] is True


def test_session_routes_start_state_text_stop(monkeypatch) -> None:
    calls: dict[str, object] = {
        "started": False,
        "stopped": False,
        "submitted": [],
    }

    class _FakeService:
        def __init__(self) -> None:
            self.state = SimpleNamespace(
                status="listening",
                session_id="session-6",
                turn_count=2,
                last_turn_id="turn-2",
                degraded_conditions=[],
                last_response="hello",
                last_transcript="hi",
            )

        def start(self, _report, _personality, _summary) -> None:
            calls["started"] = True

        def stop(self) -> None:
            calls["stopped"] = True

        def submit_text(self, text: str) -> None:
            cast_list = calls["submitted"]
            assert isinstance(cast_list, list)
            cast_list.append(text)

        def push_to_talk(self) -> None:
            calls["ptt"] = True

    fake_service = _FakeService()
    monkeypatch.setattr(session_routes, "get_startup_context", _startup_context)
    monkeypatch.setattr(session_routes, "get_session_service", lambda: fake_service)

    client = TestClient(api_main.app)

    start_response = client.post("/session/start")
    assert start_response.status_code == 200
    assert start_response.json() == {"session_id": "session-6", "status": "listening"}
    assert calls["started"] is True

    state_response = client.get("/session/state")
    assert state_response.status_code == 200
    assert state_response.json()["session_id"] == "session-6"
    assert state_response.json()["status"] == "listening"

    text_response = client.post("/session/text", json={"text": "hello"})
    assert text_response.status_code == 200
    assert text_response.json() == {"queued": True}
    assert calls["submitted"] == ["hello"]

    stop_response = client.post("/session/stop")
    assert stop_response.status_code == 200
    assert stop_response.json() == {"session_id": "session-6", "status": "stopped"}
    assert calls["stopped"] is True


def test_session_text_rejects_empty_text(monkeypatch) -> None:
    class _FakeService:
        state = SimpleNamespace(status="listening", session_id="s", turn_count=0, last_turn_id=None, degraded_conditions=[], last_response=None, last_transcript=None)

        def submit_text(self, text: str) -> None:
            raise AssertionError(f"submit_text should not be called for empty text: {text}")

    monkeypatch.setattr(session_routes, "get_session_service", lambda: _FakeService())

    client = TestClient(api_main.app)
    response = client.post("/session/text", json={"text": "   "})

    assert response.status_code == 400
    assert response.json()["detail"] == "text must not be empty"


def test_session_text_rejects_when_not_running(monkeypatch) -> None:
    class _FakeService:
        state = SimpleNamespace(status="stopped", session_id=None, turn_count=0, last_turn_id=None, degraded_conditions=[], last_response=None, last_transcript=None)

        def submit_text(self, text: str) -> None:
            raise AssertionError(f"submit_text should not be called when stopped: {text}")

    monkeypatch.setattr(session_routes, "get_session_service", lambda: _FakeService())

    client = TestClient(api_main.app)
    response = client.post("/session/text", json={"text": "hello"})

    assert response.status_code == 409
    assert response.json()["detail"] == "session is not running"


def _startup_summary() -> StartupSummary:
    return StartupSummary(
        profile_id="test-profile",
        device_class="desktop",
        stt_ready=True,
        stt_selected_device="cpu",
        tts_ready=True,
        tts_selected_device="cpu",
        llm_ready=True,
        llm_runtime_name="OllamaLLM",
        personality_profile_id="default",
        personality_display_name="JARVIS",
        degraded_conditions=[],
    )


def test_resident_session_state_defaults() -> None:
    state = session_service.ResidentSessionState()
    assert state.status == "idle"
    assert state.session_id is None
    assert state.turn_count == 0
    assert state.degraded_conditions == []
    assert state.last_response is None
    assert state.last_transcript is None


def test_session_service_start_sets_listening_and_session(monkeypatch) -> None:
    report = cast(Any, object())
    personality = cast(Any, object())
    summary = _startup_summary()
    fake_session = SimpleNamespace(session_id="session-1")

    monkeypatch.setattr(session_service.SessionManager, "open_session", staticmethod(lambda: fake_session))
    monkeypatch.setattr(session_service.SessionManager, "close_session", staticmethod(lambda _s: None))
    monkeypatch.setattr(session_service, "select_wake_runtime", lambda: None)
    monkeypatch.setattr(session_service.ResidentSessionService, "_run_loop", lambda self: None)

    svc = session_service.ResidentSessionService()
    svc.start(report, personality, summary)

    state = svc.state
    assert state.status == "listening"
    assert state.session_id == "session-1"


def test_session_service_stop_sets_stopped_and_closes_session(monkeypatch) -> None:
    report = cast(Any, object())
    personality = cast(Any, object())
    summary = _startup_summary()
    fake_session = SimpleNamespace(session_id="session-2")
    closed: list[object] = []

    monkeypatch.setattr(session_service.SessionManager, "open_session", staticmethod(lambda: fake_session))
    monkeypatch.setattr(session_service.SessionManager, "close_session", staticmethod(lambda s: closed.append(s)))
    monkeypatch.setattr(session_service, "select_wake_runtime", lambda: None)
    monkeypatch.setattr(session_service.ResidentSessionService, "_run_loop", lambda self: None)

    svc = session_service.ResidentSessionService()
    svc.start(report, personality, summary)
    svc.stop()

    assert svc.state.status == "stopped"
    assert closed == [fake_session]


def test_submit_text_enqueues_and_sets_invoke_event(monkeypatch) -> None:
    svc = session_service.ResidentSessionService()
    monkeypatch.setattr(svc, "_run_text_once", lambda _text: None)

    svc.submit_text("hello")

    assert svc._invoke_event.is_set()
    assert svc._drain_text_once() == "hello"


def test_push_to_talk_sets_shared_and_ptt_events() -> None:
    svc = session_service.ResidentSessionService()
    svc.push_to_talk()
    assert svc._invoke_event.is_set()
    assert svc._ptt_event.is_set()


def test_run_voice_once_interrupted_returns_to_listening(monkeypatch) -> None:
    fake_session = SimpleNamespace(session_id="session-3")

    svc = session_service.ResidentSessionService()
    svc._report = cast(Any, object())
    svc._personality = cast(Any, object())
    svc._session = cast(Any, fake_session)
    svc._memory = cast(Any, object())

    monkeypatch.setattr(
        session_service,
        "run_voice_turn",
        lambda *_args, **_kwargs: VoiceTurnResult(response=None, interrupted=True, interrupted_at="t"),
    )
    monkeypatch.setattr(session_service, "list_session_turns", lambda _sid: [])

    svc._run_voice_once()
    state = svc.state
    assert state.status == "listening"
    assert state.turn_count == 0


def test_run_loop_degrades_on_voice_exception(monkeypatch) -> None:
    report = cast(Any, object())
    personality = cast(Any, object())
    summary = _startup_summary()
    fake_session = SimpleNamespace(session_id="session-4")

    monkeypatch.setattr(session_service.SessionManager, "open_session", staticmethod(lambda: fake_session))
    monkeypatch.setattr(session_service.SessionManager, "close_session", staticmethod(lambda _s: None))
    monkeypatch.setattr(session_service, "select_wake_runtime", lambda: None)
    svc = session_service.ResidentSessionService()

    def _boom() -> None:
        svc._stop_event.set()
        raise RuntimeError("voice boom")

    monkeypatch.setattr(session_service.ResidentSessionService, "_run_ptt_voice_once", lambda self: _boom())
    monkeypatch.setattr(threading.Thread, "join", lambda self, timeout=None: None)

    svc.start(report, personality, summary)
    worker = svc._worker_thread
    assert worker is not None
    svc.push_to_talk()
    worker.join(timeout=2)

    state = svc.state
    for _ in range(20):
        state = svc.state
        if state.status == "degraded":
            break
        time.sleep(0.01)

    assert state.status == "degraded"
    assert any("voice boom" in item for item in state.degraded_conditions)