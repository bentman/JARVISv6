from __future__ import annotations

from types import SimpleNamespace

import scripts.run_jarvis as run_jarvis


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
