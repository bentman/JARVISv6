from __future__ import annotations

from types import SimpleNamespace
from typing import Any

import scripts.run_jarvis as run_jarvis

from backend.app.core.capabilities import (
    BackendReadiness,
    CapabilityFlags,
    FullCapabilityReport,
    HardwareProfile,
)
from backend.app.personality.schema import PersonalityProfile
from backend.app.services import startup_service
from backend.app.services import task_service


def _summary(*, stt_ready: bool, tts_ready: bool = True, llm_ready: bool = True) -> SimpleNamespace:
    return SimpleNamespace(
        stt_ready=stt_ready,
        tts_ready=tts_ready,
        llm_ready=llm_ready,
    )


def test_startup_only_turns_zero_exits_cleanly(monkeypatch) -> None:
    summary = _summary(stt_ready=True, tts_ready=True, llm_ready=True)
    report = object()
    personality = object()
    session = object()

    closed: list[object] = []

    monkeypatch.setattr(run_jarvis, "run_startup", lambda personality_name="default": (summary, report, personality))
    monkeypatch.setattr(run_jarvis, "print_startup_summary", lambda _summary: None)
    monkeypatch.setattr(run_jarvis, "select_wake_runtime", lambda: None)
    monkeypatch.setattr(run_jarvis.SessionManager, "open_session", staticmethod(lambda: session))
    monkeypatch.setattr(run_jarvis.SessionManager, "close_session", staticmethod(lambda s: closed.append(s)))

    rc = run_jarvis.main(["--turns", "0"])

    assert rc == 0
    assert closed == [session]


def test_shell_voice_gated_when_stt_not_ready(monkeypatch) -> None:
    summary = _summary(stt_ready=False, tts_ready=True, llm_ready=True)
    report = object()
    personality = object()
    session = object()

    inputs = iter(["voice", "quit"])
    prints: list[str] = []
    voice_calls: list[tuple[object, object]] = []

    monkeypatch.setattr(run_jarvis, "run_startup", lambda personality_name="default": (summary, report, personality))
    monkeypatch.setattr(run_jarvis, "print_startup_summary", lambda _summary: None)
    monkeypatch.setattr(run_jarvis, "select_wake_runtime", lambda: None)
    monkeypatch.setattr(run_jarvis.SessionManager, "open_session", staticmethod(lambda: session))
    monkeypatch.setattr(run_jarvis.SessionManager, "close_session", staticmethod(lambda _s: None))
    monkeypatch.setattr(
        run_jarvis,
        "run_voice_turn",
        lambda *_args, **_kwargs: (voice_calls.append((_args[0], _args[1])) or SimpleNamespace(interrupted=False, response="x")),
    )

    rc = run_jarvis.main(
        [],
        input_fn=lambda _prompt: next(inputs),
        print_fn=lambda *args: prints.append(" ".join(str(a) for a in args)),
    )

    assert rc == 0
    assert voice_calls == []
    assert any("Voice unavailable (STT not ready)" in line for line in prints)


def test_text_dispatch_and_turn_cap(monkeypatch) -> None:
    summary = _summary(stt_ready=True, tts_ready=True, llm_ready=True)
    report = object()
    personality = object()
    session = object()

    text_calls: list[dict[str, object]] = []
    closed: list[object] = []

    def _fake_text_turn(text, report_arg, personality_arg, *, session=None, memory=None):
        text_calls.append(
            {
                "text": text,
                "report": report_arg,
                "personality": personality_arg,
                "session": session,
                "memory": memory,
            }
        )
        return SimpleNamespace(response="ok", failed=False, failure_reason=None)

    monkeypatch.setattr(run_jarvis, "run_startup", lambda personality_name="default": (summary, report, personality))
    monkeypatch.setattr(run_jarvis, "print_startup_summary", lambda _summary: None)
    monkeypatch.setattr(run_jarvis, "select_wake_runtime", lambda: None)
    monkeypatch.setattr(run_jarvis.SessionManager, "open_session", staticmethod(lambda: session))
    monkeypatch.setattr(run_jarvis.SessionManager, "close_session", staticmethod(lambda s: closed.append(s)))
    monkeypatch.setattr(run_jarvis, "run_text_turn", _fake_text_turn)

    rc = run_jarvis.main(["--turns", "1"], input_fn=lambda _prompt: "hello", print_fn=lambda *args: None)

    assert rc == 0
    assert len(text_calls) == 1
    assert text_calls[0]["text"] == "hello"
    assert text_calls[0]["report"] is report
    assert text_calls[0]["personality"] is personality
    assert text_calls[0]["session"] is session
    assert text_calls[0]["memory"] is not None
    assert closed == [session]


def test_shared_session_memory_forwarding_across_text_and_voice(monkeypatch) -> None:
    summary = _summary(stt_ready=True, tts_ready=True, llm_ready=True)
    report = object()
    personality = object()
    session = object()

    seen: dict[str, object] = {}

    inputs = iter(["hello", "voice"])

    def _fake_text_turn(text, report_arg, personality_arg, *, session=None, memory=None):
        seen["text"] = text
        seen["text_report"] = report_arg
        seen["text_personality"] = personality_arg
        seen["text_session"] = session
        seen["text_memory"] = memory
        return SimpleNamespace(response="text", failed=False, failure_reason=None)

    def _fake_voice_turn(report_arg, personality_arg, *, session=None, memory=None):
        seen["voice_report"] = report_arg
        seen["voice_personality"] = personality_arg
        seen["voice_session"] = session
        seen["voice_memory"] = memory
        return SimpleNamespace(response="voice", interrupted=False)

    monkeypatch.setattr(run_jarvis, "run_startup", lambda personality_name="default": (summary, report, personality))
    monkeypatch.setattr(run_jarvis, "print_startup_summary", lambda _summary: None)
    monkeypatch.setattr(run_jarvis, "select_wake_runtime", lambda: None)
    monkeypatch.setattr(run_jarvis.SessionManager, "open_session", staticmethod(lambda: session))
    monkeypatch.setattr(run_jarvis.SessionManager, "close_session", staticmethod(lambda _s: None))
    monkeypatch.setattr(run_jarvis, "run_text_turn", _fake_text_turn)
    monkeypatch.setattr(run_jarvis, "run_voice_turn", _fake_voice_turn)

    rc = run_jarvis.main(["--turns", "2"], input_fn=lambda _prompt: next(inputs), print_fn=lambda *args: None)

    assert rc == 0
    assert seen["text"] == "hello"
    assert seen["text_report"] is report
    assert seen["text_personality"] is personality
    assert seen["voice_report"] is report
    assert seen["voice_personality"] is personality
    assert seen["text_session"] is session
    assert seen["voice_session"] is session
    assert seen["text_memory"] is seen["voice_memory"]


def test_wake_unavailable_prints_startup_message_and_text_flow_still_works(monkeypatch) -> None:
    summary = _summary(stt_ready=True, tts_ready=True, llm_ready=True)
    report = object()
    personality = object()
    session = object()

    prints: list[str] = []
    text_calls: list[str] = []

    monkeypatch.setattr(run_jarvis, "run_startup", lambda personality_name="default": (summary, report, personality))
    monkeypatch.setattr(run_jarvis, "print_startup_summary", lambda _summary: None)
    monkeypatch.setattr(run_jarvis, "select_wake_runtime", lambda: None)
    monkeypatch.setattr(run_jarvis.SessionManager, "open_session", staticmethod(lambda: session))
    monkeypatch.setattr(run_jarvis.SessionManager, "close_session", staticmethod(lambda _s: None))
    monkeypatch.setattr(
        run_jarvis,
        "run_text_turn",
        lambda text, *_args, **_kwargs: (text_calls.append(text) or SimpleNamespace(response="ok", failed=False, failure_reason=None)),
    )

    inputs = iter(["hello", "quit"])
    rc = run_jarvis.main(
        [],
        input_fn=lambda _prompt: next(inputs),
        print_fn=lambda *args: prints.append(" ".join(str(a) for a in args)),
    )

    assert rc == 0
    assert any("⚠ WAKE WORD: unavailable (push-to-talk mode)" in line for line in prints)
    assert text_calls == ["hello"]


def test_wake_flag_triggers_voice_turn_without_manual_voice_command(monkeypatch) -> None:
    summary = _summary(stt_ready=True, tts_ready=True, llm_ready=True)
    report = object()
    personality = object()
    session = object()

    voice_calls: list[tuple[object, object]] = []

    class _WakeRuntime:
        failed = False
        failure_reason = None

        def start(self, wake_flag) -> None:
            wake_flag.set()

        def stop(self) -> None:
            pass

    monkeypatch.setattr(run_jarvis, "run_startup", lambda personality_name="default": (summary, report, personality))
    monkeypatch.setattr(run_jarvis, "print_startup_summary", lambda _summary: None)
    monkeypatch.setattr(run_jarvis, "select_wake_runtime", lambda: _WakeRuntime())
    monkeypatch.setattr(run_jarvis.SessionManager, "open_session", staticmethod(lambda: session))
    monkeypatch.setattr(run_jarvis.SessionManager, "close_session", staticmethod(lambda _s: None))
    monkeypatch.setattr(
        run_jarvis,
        "run_voice_turn",
        lambda report_arg, personality_arg, **_kwargs: (
            voice_calls.append((report_arg, personality_arg))
            or SimpleNamespace(interrupted=False, response="voice")
        ),
    )

    rc = run_jarvis.main(["--turns", "1"], input_fn=lambda _prompt: next(iter(())), print_fn=lambda *args: None)

    assert rc == 0
    assert len(voice_calls) == 1


def test_wake_trigger_counts_toward_turn_limit(monkeypatch) -> None:
    summary = _summary(stt_ready=True, tts_ready=True, llm_ready=True)
    report = object()
    personality = object()
    session = object()

    voice_calls: list[str] = []
    text_calls: list[str] = []

    class _WakeRuntime:
        failed = False
        failure_reason = None

        def start(self, wake_flag) -> None:
            wake_flag.set()

        def stop(self) -> None:
            pass

    monkeypatch.setattr(run_jarvis, "run_startup", lambda personality_name="default": (summary, report, personality))
    monkeypatch.setattr(run_jarvis, "print_startup_summary", lambda _summary: None)
    monkeypatch.setattr(run_jarvis, "select_wake_runtime", lambda: _WakeRuntime())
    monkeypatch.setattr(run_jarvis.SessionManager, "open_session", staticmethod(lambda: session))
    monkeypatch.setattr(run_jarvis.SessionManager, "close_session", staticmethod(lambda _s: None))
    monkeypatch.setattr(
        run_jarvis,
        "run_voice_turn",
        lambda *_args, **_kwargs: (voice_calls.append("voice") or SimpleNamespace(interrupted=False, response="voice")),
    )
    monkeypatch.setattr(
        run_jarvis,
        "run_text_turn",
        lambda text, *_args, **_kwargs: (text_calls.append(text) or SimpleNamespace(response="ok", failed=False, failure_reason=None)),
    )

    inputs = iter(["hello"])
    rc = run_jarvis.main(["--turns", "2"], input_fn=lambda _prompt: next(inputs), print_fn=lambda *args: None)

    assert rc == 0
    assert voice_calls == ["voice"]
    assert text_calls == ["hello"]


def test_wake_runtime_stop_called_on_exit(monkeypatch) -> None:
    summary = _summary(stt_ready=True, tts_ready=True, llm_ready=True)
    report = object()
    personality = object()
    session = object()

    class _WakeRuntime:
        failed = False
        failure_reason = None

        def __init__(self) -> None:
            self.stopped = False

        def start(self, wake_flag) -> None:
            return None

        def stop(self) -> None:
            self.stopped = True

    wake_runtime = _WakeRuntime()

    monkeypatch.setattr(run_jarvis, "run_startup", lambda personality_name="default": (summary, report, personality))
    monkeypatch.setattr(run_jarvis, "print_startup_summary", lambda _summary: None)
    monkeypatch.setattr(run_jarvis, "select_wake_runtime", lambda: wake_runtime)
    monkeypatch.setattr(run_jarvis.SessionManager, "open_session", staticmethod(lambda: session))
    monkeypatch.setattr(run_jarvis.SessionManager, "close_session", staticmethod(lambda _s: None))

    rc = run_jarvis.main(["--turns", "0"])

    assert rc == 0
    assert wake_runtime.stopped is True


def _report(*, stt_selected_device: str = "cpu", tts_selected_device: str = "cpu") -> FullCapabilityReport:
    return FullCapabilityReport(
        profile=HardwareProfile(
            os="Windows",
            arch="AMD64",
            cpu_name="unit-cpu",
            cpu_physical_cores=8,
            cpu_logical_cores=16,
            cpu_max_freq_mhz=3000.0,
            gpu_available=True,
            gpu_name="NVIDIA",
            gpu_vendor="nvidia",
            gpu_vram_gb=12.0,
            cuda_available=True,
            npu_available=False,
            npu_vendor=None,
            npu_tops=None,
            memory_total_gb=32.0,
            memory_available_gb=20.0,
            device_class="desktop",
            profile_id="nvidia-cuda-desktop-32gb",
        ),
        flags=CapabilityFlags(
            supports_local_llm=True,
            supports_gpu_llm=True,
            supports_cuda_llm=True,
            supports_local_stt=True,
            supports_local_tts=True,
            supports_wake_word=False,
            supports_realtime_voice=True,
            supports_desktop_shell=True,
            requires_degraded_mode=False,
        ),
        readiness=BackendReadiness(
            stt_cuda_ready=stt_selected_device == "cuda",
            stt_cpu_ready=stt_selected_device == "cpu",
            stt_selected_device=stt_selected_device,
            tts_cuda_ready=tts_selected_device == "cuda",
            tts_cpu_ready=tts_selected_device == "cpu",
            tts_selected_device=tts_selected_device,
            llm_local_ready=False,
            llm_service_ready=False,
            llm_selected_runtime="unavailable",
        ),
    )


def _personality() -> PersonalityProfile:
    return PersonalityProfile(
        profile_id="default",
        display_name="J.A.R.V.I.S.",
        identity_summary="A direct, capable local assistant.",
        tone="neutral",
        brevity="concise",
        formality="professional",
        warmth="measured",
        assertiveness="moderate",
        humor_policy="none",
        response_style="direct",
        acknowledgment_style="minimal",
        interruption_style="stop-and-listen",
        voice_pacing="moderate",
        voice_energy="calm",
        safety_overrides=[],
        enabled=True,
    )


def test_startup_summary_contract_fields_present() -> None:
    fields = startup_service.StartupSummary.__dataclass_fields__
    assert "profile_id" in fields
    assert "device_class" in fields
    assert "stt_ready" in fields
    assert "stt_selected_device" in fields
    assert "tts_ready" in fields
    assert "tts_selected_device" in fields
    assert "llm_ready" in fields
    assert "llm_runtime_name" in fields
    assert "personality_profile_id" in fields
    assert "personality_display_name" in fields
    assert "degraded_conditions" in fields
    assert "voice_name" not in fields


def test_run_startup_returns_summary_report_personality(monkeypatch) -> None:
    monkeypatch.setattr(startup_service, "run_profiler", lambda: _report())
    monkeypatch.setattr(startup_service, "load_personality_profile", lambda _name: _personality())

    class _ReadyOllama:
        def is_available(self) -> bool:
            return True

    monkeypatch.setattr(startup_service, "OllamaLLM", _ReadyOllama)

    summary, report, personality = startup_service.run_startup()

    assert isinstance(summary, startup_service.StartupSummary)
    assert isinstance(report, FullCapabilityReport)
    assert isinstance(personality, PersonalityProfile)
    assert summary.stt_ready is True
    assert summary.tts_ready is True
    assert summary.llm_ready is True
    assert summary.llm_runtime_name == "OllamaLLM"
    assert summary.degraded_conditions == []


def test_run_startup_degraded_conditions_for_unavailable_paths(monkeypatch) -> None:
    monkeypatch.setattr(
        startup_service,
        "run_profiler",
        lambda: _report(stt_selected_device="unavailable", tts_selected_device="unavailable"),
    )
    monkeypatch.setattr(startup_service, "load_personality_profile", lambda _name: _personality())

    class _UnavailableOllama:
        def is_available(self) -> bool:
            return False

    monkeypatch.setattr(startup_service, "OllamaLLM", _UnavailableOllama)

    summary, _, _ = startup_service.run_startup()

    assert summary.stt_ready is False
    assert summary.tts_ready is False
    assert summary.llm_ready is False
    assert summary.llm_runtime_name == "unavailable"
    assert "STT unavailable (no ready selected device)" in summary.degraded_conditions
    assert "TTS unavailable (no ready selected device)" in summary.degraded_conditions
    assert "LLM service unavailable (Ollama not reachable)" in summary.degraded_conditions


def test_print_startup_summary_renders_without_voice_fields(capsys) -> None:
    summary = startup_service.StartupSummary(
        profile_id="nvidia-cuda-desktop-32gb",
        device_class="desktop",
        stt_ready=True,
        stt_selected_device="cuda",
        tts_ready=True,
        tts_selected_device="cpu",
        llm_ready=False,
        llm_runtime_name="unavailable",
        personality_profile_id="default",
        personality_display_name="J.A.R.V.I.S.",
        degraded_conditions=["LLM service unavailable (Ollama not reachable)"],
    )

    startup_service.print_startup_summary(summary)
    captured = capsys.readouterr().out

    assert "Profile:" in captured
    assert "Personality:" in captured
    assert "DEGRADED:" in captured
    assert "voice:" not in captured.lower()


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