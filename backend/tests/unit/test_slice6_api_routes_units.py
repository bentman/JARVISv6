from __future__ import annotations

from types import SimpleNamespace

from fastapi.testclient import TestClient

from backend.app.api import main as api_main
from backend.app.api.routes import health as health_routes
from backend.app.api.routes import session as session_routes


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
