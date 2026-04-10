from __future__ import annotations

import argparse
import sys
import threading
from queue import Empty, SimpleQueue
from pathlib import Path
from typing import Callable

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from backend.app.conversation.session_manager import SessionManager
from backend.app.memory.working import WorkingMemory
from backend.app.services.startup_service import print_startup_summary, run_startup
from backend.app.services.task_service import run_text_turn
from backend.app.services.voice_service import run_voice_turn
from backend.app.runtimes.wake.wakeword_runtime import select_wake_runtime


def _stdin_reader(input_fn: Callable[[str], str], cmd_queue: SimpleQueue[str]) -> None:
    while True:
        try:
            cmd_queue.put(input_fn("> "))
        except (EOFError, StopIteration):
            cmd_queue.put("__EOF__")
            return


def main(
    argv: list[str] | None = None,
    *,
    input_fn: Callable[[str], str] = input,
    print_fn: Callable[..., None] = print,
) -> int:
    parser = argparse.ArgumentParser(description="Bounded local shell adapter for JARVIS start-path validation")
    parser.add_argument("--personality", default="default")
    parser.add_argument("--turns", type=int, default=None)
    args = parser.parse_args(argv)

    if args.turns is not None and args.turns < 0:
        print_fn("[FAILED] --turns must be >= 0")
        return 1

    summary, report, personality = run_startup(personality_name=args.personality)
    print_startup_summary(summary)

    if not summary.stt_ready and not summary.tts_ready and not summary.llm_ready:
        print_fn("[FAILED] STT, TTS, and LLM are all unavailable")
        return 1

    session = SessionManager.open_session()
    memory = WorkingMemory(max_turns=5)

    turns_completed = 0
    turn_limit = args.turns
    wake_flag = threading.Event()
    wake_runtime = select_wake_runtime()

    if wake_runtime is None:
        print_fn("⚠ WAKE WORD: unavailable (push-to-talk mode)")
    else:
        wake_runtime.start(wake_flag)
        if wake_runtime.failed:
            print_fn("⚠ WAKE WORD: unavailable (push-to-talk mode)")
            wake_runtime = None
        else:
            print_fn("[WAKE] ready")

    cmd_queue: SimpleQueue[str] = SimpleQueue()
    stdin_thread = threading.Thread(target=_stdin_reader, args=(input_fn, cmd_queue), daemon=True)
    stdin_thread.start()

    def _run_voice_turn_once() -> bool:
        nonlocal turns_completed
        if not summary.stt_ready:
            print_fn("[DEGRADED] Voice unavailable (STT not ready) — enter text instead")
            return False

        voice_result = run_voice_turn(
            report,
            personality,
            session=session,
            memory=memory,
        )
        if voice_result.interrupted:
            print_fn("[INTERRUPTED]")
        elif voice_result.response:
            print_fn(f"[RESPONSE] {voice_result.response}")

        turns_completed += 1
        return True

    try:
        if turn_limit == 0:
            return 0

        while True:
            if turn_limit is not None and turns_completed >= turn_limit:
                print_fn("[EXIT] turn limit reached")
                return 0

            if wake_runtime is not None and wake_flag.is_set():
                print_fn("[WAKE] trigger consumed")
                wake_flag.clear()
                print_fn("[WAKE] dispatch voice turn")
                _run_voice_turn_once()
                continue

            try:
                user_input = cmd_queue.get(timeout=0.1)
            except Empty:
                continue

            if user_input == "__EOF__":
                return 0

            user_input = user_input.strip()

            if not user_input:
                continue

            normalized = user_input.lower()
            if normalized in {"q", "quit", "exit"}:
                return 0

            if normalized in {"v", "voice"}:
                _run_voice_turn_once()
                continue

            text_result = run_text_turn(
                user_input,
                report,
                personality,
                session=session,
                memory=memory,
            )
            if text_result.failed:
                print_fn(f"[FAILED] text turn: {text_result.failure_reason}")
            else:
                print_fn(f"[RESPONSE] {text_result.response}")

            turns_completed += 1
    finally:
        if wake_runtime is not None:
            wake_runtime.stop()
        SessionManager.close_session(session)


if __name__ == "__main__":
    raise SystemExit(main())
