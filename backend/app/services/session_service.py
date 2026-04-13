from __future__ import annotations

from dataclasses import dataclass, field, replace
from queue import Empty, SimpleQueue
import threading

from backend.app.artifacts.storage import list_session_turns, read_turn_artifact
from backend.app.conversation.session_manager import Session, SessionManager
from backend.app.core.capabilities import FullCapabilityReport
from backend.app.memory.working import WorkingMemory
from backend.app.personality.schema import PersonalityProfile
from backend.app.runtimes.wake.base import WakeWordBase
from backend.app.runtimes.wake.wakeword_runtime import select_wake_runtime
from backend.app.services.startup_service import StartupSummary
from backend.app.services.task_service import run_text_turn
from backend.app.services.voice_service import run_voice_turn


@dataclass(slots=True)
class ResidentSessionState:
    status: str = "idle"
    session_id: str | None = None
    turn_count: int = 0
    degraded_conditions: list[str] = field(default_factory=list)
    last_response: str | None = None
    last_transcript: str | None = None


class ResidentSessionService:
    """Owns resident session lifecycle and invocation loop for one assistant run."""

    def __init__(self) -> None:
        self._lock = threading.RLock()
        self._state = ResidentSessionState()

        self._session: Session | None = None
        self._memory: WorkingMemory | None = None
        self._report: FullCapabilityReport | None = None
        self._personality: PersonalityProfile | None = None
        self._summary: StartupSummary | None = None

        self._text_queue: SimpleQueue[str] = SimpleQueue()
        self._invoke_event = threading.Event()
        self._wake_flag = threading.Event()
        self._stop_event = threading.Event()

        self._worker_thread: threading.Thread | None = None
        self._wake_runtime: WakeWordBase | None = None

    def start(
        self,
        report: FullCapabilityReport,
        personality: PersonalityProfile,
        summary: StartupSummary,
    ) -> None:
        with self._lock:
            if self._worker_thread is not None and self._worker_thread.is_alive():
                return

            self._report = report
            self._personality = personality
            self._summary = summary

            self._session = SessionManager.open_session()
            self._memory = WorkingMemory(max_turns=5)

            self._stop_event.clear()
            self._invoke_event.clear()
            self._wake_flag.clear()

            self._state = ResidentSessionState(
                status="listening",
                session_id=self._session.session_id,
                turn_count=0,
                degraded_conditions=list(summary.degraded_conditions),
                last_response=None,
                last_transcript=None,
            )

            self._wake_runtime = select_wake_runtime()
            if self._wake_runtime is not None:
                self._wake_runtime.start(self._wake_flag)
                if self._wake_runtime.failed:
                    reason = self._wake_runtime.failure_reason or "wake runtime unavailable"
                    self._state.degraded_conditions.append(f"Wake unavailable: {reason}")
                    self._wake_runtime = None

            self._worker_thread = threading.Thread(
                target=self._run_loop,
                name="resident-session-loop",
                daemon=True,
            )
            self._worker_thread.start()

            # Resident loop owns listening cycle: prime first invocation.
            self._invoke_event.set()

    def stop(self) -> None:
        with self._lock:
            self._stop_event.set()
            self._invoke_event.set()
            worker = self._worker_thread

        if worker is not None:
            worker.join(timeout=10)

        with self._lock:
            if self._wake_runtime is not None:
                self._wake_runtime.stop()
                self._wake_runtime = None

            if self._session is not None:
                SessionManager.close_session(self._session)

            self._worker_thread = None
            self._session = None
            self._memory = None
            self._report = None
            self._personality = None
            self._summary = None

            self._state.status = "stopped"
            self._state.session_id = None

    def submit_text(self, text: str) -> None:
        value = text.strip()
        if not value:
            return
        self._text_queue.put(value)
        self._invoke_event.set()

    def push_to_talk(self) -> None:
        """Queue one invocation trigger through the shared resident invocation path."""
        self._invoke_event.set()

    @property
    def state(self) -> ResidentSessionState:
        with self._lock:
            return replace(self._state, degraded_conditions=list(self._state.degraded_conditions))

    def _run_loop(self) -> None:
        while not self._stop_event.is_set():
            try:
                self._sync_wake_trigger()

                # Process queued text first so typed fallback is responsive.
                text_item = self._drain_text_once()
                if text_item is not None:
                    self._run_text_once(text_item)
                    continue

                if not self._invoke_event.wait(timeout=0.2):
                    continue
                self._invoke_event.clear()

                if self._stop_event.is_set():
                    break

                # wake flag + push-to-talk converge here.
                self._wake_flag.clear()
                self._run_voice_once()
            except Exception as exc:  # fail degraded, not dead
                with self._lock:
                    self._state.status = "degraded"
                    self._state.degraded_conditions.append(str(exc))

        with self._lock:
            if self._state.status not in {"stopped", "degraded"}:
                self._state.status = "listening"

    def _sync_wake_trigger(self) -> None:
        if self._wake_flag.is_set():
            self._invoke_event.set()

    def _drain_text_once(self) -> str | None:
        try:
            return self._text_queue.get_nowait()
        except Empty:
            return None

    def _run_text_once(self, text: str) -> None:
        with self._lock:
            if self._report is None or self._personality is None:
                return
            self._state.status = "thinking"
            report = self._report
            personality = self._personality
            session = self._session
            memory = self._memory

        result = run_text_turn(
            text,
            report,
            personality,
            session=session,
            memory=memory,
        )

        with self._lock:
            self._state.last_transcript = text
            if result.failed:
                self._state.status = "degraded"
                self._state.degraded_conditions.append(result.failure_reason or "text turn failed")
            else:
                self._state.last_response = result.response
                self._state.turn_count += 1
                self._state.status = "listening"

    def _run_voice_once(self) -> None:
        with self._lock:
            if self._report is None or self._personality is None:
                return
            self._state.status = "listening"
            report = self._report
            personality = self._personality
            session = self._session
            memory = self._memory

        result = run_voice_turn(
            report,
            personality,
            session=session,
            memory=memory,
        )

        with self._lock:
            if result.interrupted:
                self._state.status = "listening"
                self._state.turn_count += 1
            else:
                self._state.status = "listening"
                if result.response is not None:
                    self._state.last_response = result.response
                    self._state.turn_count += 1

            if session is not None:
                turn_ids = list_session_turns(session.session_id)
                if turn_ids:
                    artifact = read_turn_artifact(session.session_id, turn_ids[-1])
                    self._state.last_transcript = artifact.transcript