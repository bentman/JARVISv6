from __future__ import annotations

import argparse
import sys
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

    try:
        if turn_limit == 0:
            return 0

        while True:
            if turn_limit is not None and turns_completed >= turn_limit:
                return 0

            try:
                user_input = input_fn("> ").strip()
            except EOFError:
                return 0

            if not user_input:
                continue

            normalized = user_input.lower()
            if normalized in {"q", "quit", "exit"}:
                return 0

            if normalized in {"v", "voice"}:
                if not summary.stt_ready:
                    print_fn("[DEGRADED] Voice unavailable (STT not ready) — enter text instead")
                    continue

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
        SessionManager.close_session(session)


if __name__ == "__main__":
    raise SystemExit(main())
