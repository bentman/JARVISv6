from __future__ import annotations

from dataclasses import dataclass
from threading import Lock

from backend.app.core.capabilities import FullCapabilityReport
from backend.app.personality.schema import PersonalityProfile
from backend.app.services.session_service import ResidentSessionService
from backend.app.services.startup_service import StartupSummary, run_startup


@dataclass(slots=True)
class StartupContext:
    summary: StartupSummary
    report: FullCapabilityReport
    personality: PersonalityProfile


_deps_lock = Lock()
_startup_context: StartupContext | None = None
_startup_error: str | None = None
_session_service: ResidentSessionService | None = None


def set_startup_error(error: str) -> None:
    global _startup_error
    with _deps_lock:
        _startup_error = error


def get_startup_error() -> str | None:
    with _deps_lock:
        return _startup_error


def is_startup_context_ready() -> bool:
    with _deps_lock:
        return _startup_context is not None


def get_startup_context_if_ready() -> StartupContext | None:
    with _deps_lock:
        return _startup_context


def get_startup_context() -> StartupContext:
    global _startup_context
    with _deps_lock:
        if _startup_context is None:
            summary, report, personality = run_startup()
            _startup_context = StartupContext(
                summary=summary,
                report=report,
                personality=personality,
            )
        return _startup_context


def get_session_service() -> ResidentSessionService:
    global _session_service
    with _deps_lock:
        if _session_service is None:
            _session_service = ResidentSessionService()
        return _session_service
