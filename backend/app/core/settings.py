from __future__ import annotations

import os
from pathlib import Path


def _read_env_file_value(key: str) -> str | None:
    env_path = Path(".env")
    if not env_path.exists():
        return None

    try:
        for raw_line in env_path.read_text(encoding="utf-8").splitlines():
            line = raw_line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            candidate_key, candidate_value = line.split("=", 1)
            if candidate_key.strip() != key:
                continue
            value = candidate_value.strip()
            if len(value) >= 2 and value[0] == value[-1] and value[0] in {'"', "'"}:
                value = value[1:-1]
            return value or None
    except Exception:
        return None

    return None


def _env_or_dotenv(key: str) -> str | None:
    return os.environ.get(key) or _read_env_file_value(key)


OLLAMA_MODEL: str = os.environ.get("OLLAMA_MODEL", "phi3:mini")
OLLAMA_HOST: str = os.environ.get("OLLAMA_BASE_URL", "http://localhost:11434")
LLAMA_CPP_MODEL_PATH: str | None = os.environ.get("LLAMA_CPP_MODEL_PATH") or None
PICOVOICE_ACCESS_KEY: str | None = _env_or_dotenv("PICOVOICE_ACCESS_KEY")
PVPORCUPINE_MODEL_PATH: str | None = _env_or_dotenv("PVPORCUPINE_MODEL_PATH")
