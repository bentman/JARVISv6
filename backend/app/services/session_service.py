from __future__ import annotations

from dataclasses import dataclass, field, replace
from queue import Empty, SimpleQueue
import threading
import time

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
    wake_active: bool = False
    turn_count: int = 0
    last_turn_id: str | None = None
    degraded_conditions: list[str] = field(default_factory=list)
    last_response: str | None = None
    last_transcript: str | None = None


class ResidentSessionService:
    """Owns resident session lifecycle and invocation loop for one assistant run."""

    _PTT_WARMUP_SECONDS = 0.35

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
        self._ptt_event = threading.Event()
        self._wake_flag = threading.Event()
        self._stop_event = threading.Event()
        self._wake_runtime: WakeWordBase | None = None

        self._worker_thread: threading.Thread | None = None
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
            self._ptt_event.clear()
            self._wake_flag.clear()

            self._state = ResidentSessionState(
                status="listening",
                session_id=self._session.session_id,
                wake_active=False,
                turn_count=0,
                last_turn_id=None,
                degraded_conditions=list(summary.degraded_conditions),
                last_response=None,
                last_transcript=None,
            )

            self._wake_runtime = None
            try:
                wake_runtime = select_wake_runtime()
                if wake_runtime is None:
                    self._state.degraded_conditions.append("wake word unavailable; using PTT/hotkey")
                else:
                    wake_runtime.start(self._wake_flag)
                    if wake_runtime.failed:
                        self._state.degraded_conditions.append(
                            f"wake word unavailable; using PTT/hotkey ({wake_runtime.failure_reason or 'runtime start failed'})"
                        )
                        wake_runtime.stop()
                    else:
                        self._wake_runtime = wake_runtime
                        self._state.wake_active = True
            except Exception as exc:
                self._state.degraded_conditions.append(f"wake word unavailable; using PTT/hotkey ({exc})")

            self._worker_thread = threading.Thread(
                target=self._run_loop,
                name="resident-session-loop",
                daemon=True,
            )
            self._worker_thread.start()

    def stop(self) -> None:
        with self._lock:
            self._stop_event.set()
            self._invoke_event.set()
            self._ptt_event.set()
            wake_runtime = self._wake_runtime
            self._wake_runtime = None
            self._state.wake_active = False
            worker = self._worker_thread

        if wake_runtime is not None:
            wake_runtime.stop()

        if worker is not None:
            worker.join(timeout=10)

        with self._lock:
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
            self._state.last_turn_id = None

    def submit_text(self, text: str) -> None:
        value = text.strip()
        if not value:
            return
        self._text_queue.put(value)
        self._invoke_event.set()

    def push_to_talk(self) -> None:
        """Queue one explicit PTT invocation through a dedicated resident path."""
        self._ptt_event.set()
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

                is_ptt_trigger = self._ptt_event.is_set()

                # Event may have been raised by typed input while waiting.
                text_item = self._drain_text_once()
                if text_item is not None:
                    self._run_text_once(text_item)
                    continue

                if is_ptt_trigger:
                    self._ptt_event.clear()
                    self._run_ptt_voice_once()
                    continue

                # wake flag + generic invocation converge here.
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

    def _sync_last_turn_from_artifacts(self, session: Session | None) -> bool:
        if session is None:
            return False

        turn_ids = list_session_turns(session.session_id)
        if not turn_ids:
            return False

        last_turn_id = turn_ids[-1]
        artifact = read_turn_artifact(session.session_id, last_turn_id)
        self._state.last_turn_id = last_turn_id
        self._state.last_transcript = artifact.transcript
        self._state.last_response = artifact.response_text
        self._state.turn_count = max(self._state.turn_count, int(artifact.turn_index) + 1)
        return True

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
                if not self._sync_last_turn_from_artifacts(session):
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
            else:
                self._state.status = "listening"

            if not self._sync_last_turn_from_artifacts(session):
                if result.response is not None:
                    self._state.last_response = result.response
                    self._state.turn_count += 1

    def _run_ptt_voice_once(self) -> None:
        with self._lock:
            if self._report is None or self._personality is None:
                return

        time.sleep(self._PTT_WARMUP_SECONDS)
        self._run_voice_once()