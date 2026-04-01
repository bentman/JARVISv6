from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4


@dataclass
class Session:
    session_id: str
    started_at: str
    ended_at: str | None
    turn_count: int


def _iso_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _sessions_dir() -> Path:
    return Path("data") / "sessions"


def _session_path(session_id: str) -> Path:
    return _sessions_dir() / f"{session_id}.json"


def _write_session_state(session: Session) -> None:
    sessions_dir = _sessions_dir()
    sessions_dir.mkdir(parents=True, exist_ok=True)

    path = _session_path(session.session_id)
    tmp_path = path.with_suffix(path.suffix + ".tmp")

    tmp_path.write_text(json.dumps(asdict(session), indent=2), encoding="utf-8")
    tmp_path.replace(path)


class SessionManager:
    @staticmethod
    def open_session() -> Session:
        session = Session(
            session_id=str(uuid4()),
            started_at=_iso_now(),
            ended_at=None,
            turn_count=0,
        )
        _write_session_state(session)
        return session

    @staticmethod
    def increment_turn(session: Session) -> Session:
        session.turn_count += 1
        _write_session_state(session)
        return session

    @staticmethod
    def close_session(session: Session) -> Session:
        session.ended_at = _iso_now()
        _write_session_state(session)
        return session