from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml


def load_stt_catalog(config_path: str = "config/models/stt.yaml") -> dict[str, Any]:
    path = Path(config_path)
    if not path.exists():
        raise FileNotFoundError(f"STT catalog not found: {config_path}")
    raw = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(raw, dict):
        raise ValueError(f"STT catalog invalid: expected mapping at root ({config_path})")
    return raw


def get_model_entry(
    model_name: str,
    config_path: str = "config/models/stt.yaml",
) -> dict[str, Any]:
    catalog = load_stt_catalog(config_path=config_path)
    models = catalog.get("models")
    if not isinstance(models, dict):
        raise ValueError(f"STT catalog invalid: missing models mapping ({config_path})")
    entry = models.get(model_name)
    if not isinstance(entry, dict):
        raise KeyError(f"STT model not found in catalog: {model_name}")
    return entry


def load_tts_catalog(config_path: str = "config/models/tts.yaml") -> dict[str, Any]:
    path = Path(config_path)
    if not path.exists():
        raise FileNotFoundError(f"TTS catalog not found: {config_path}")
    raw = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(raw, dict):
        raise ValueError(f"TTS catalog invalid: expected mapping at root ({config_path})")
    return raw


def get_tts_model_entry(
    model_name: str,
    config_path: str = "config/models/tts.yaml",
) -> dict[str, Any]:
    catalog = load_tts_catalog(config_path=config_path)
    models = catalog.get("models")
    if not isinstance(models, dict):
        raise ValueError(f"TTS catalog invalid: missing models mapping ({config_path})")
    entry = models.get(model_name)
    if not isinstance(entry, dict):
        raise KeyError(f"TTS model not found in catalog: {model_name}")
    return entry
