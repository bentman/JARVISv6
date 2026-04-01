from __future__ import annotations

from dataclasses import dataclass


@dataclass
class TurnSummary:
    turn_index: int
    transcript: str
    response_text: str


class WorkingMemory:
    def __init__(self, max_turns: int = 5):
        self._max_turns = max_turns
        self._turns: list[TurnSummary] = []

    def add_turn(self, summary: TurnSummary) -> None:
        self._turns.append(summary)
        if len(self._turns) > self._max_turns:
            self._turns.pop(0)

    def get_context_turns(self) -> list[TurnSummary]:
        return list(self._turns)

    def clear(self) -> None:
        self._turns.clear()