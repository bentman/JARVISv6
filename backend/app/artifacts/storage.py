from __future__ import annotations

import json
from dataclasses import asdict
from pathlib import Path

from .turn_artifact import TurnArtifact


def _session_turns_dir(session_id: str) -> Path:
    return Path("data") / "turns" / session_id


def _artifact_path(session_id: str, turn_id: str) -> Path:
    return _session_turns_dir(session_id) / f"{turn_id}.json"


def write_turn_artifact(artifact: TurnArtifact) -> str:
    turns_dir = _session_turns_dir(artifact.session_id)
    turns_dir.mkdir(parents=True, exist_ok=True)

    path = _artifact_path(artifact.session_id, artifact.turn_id)
    tmp_path = path.with_suffix(path.suffix + ".tmp")

    tmp_path.write_text(json.dumps(asdict(artifact), indent=2), encoding="utf-8")
    tmp_path.replace(path)
    return str(path)


def read_turn_artifact(session_id: str, turn_id: str) -> TurnArtifact:
    path = _artifact_path(session_id, turn_id)
    payload = json.loads(path.read_text(encoding="utf-8"))
    return TurnArtifact(**payload)


def list_session_turns(session_id: str) -> list[str]:
    turns_dir = _session_turns_dir(session_id)
    if not turns_dir.exists():
        return []

    ordered = []
    for artifact_path in turns_dir.glob("*.json"):
        payload = json.loads(artifact_path.read_text(encoding="utf-8"))
        ordered.append((int(payload.get("turn_index", 0)), artifact_path.stem))

    ordered.sort(key=lambda item: (item[0], item[1]))
    return [turn_id for _, turn_id in ordered]