from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from backend.app.models.catalog import load_stt_catalog, load_tts_catalog
from backend.app.models.manager import ModelNotAvailableError, ensure_model, verify_model


def _iter_stt_targets(model: str | None, all_models: bool) -> list[tuple[str, dict]]:
    catalog = load_stt_catalog()
    models = catalog.get("models")
    if not isinstance(models, dict):
        raise ValueError("Invalid STT catalog: missing models mapping")

    if all_models:
        return [(name, entry) for name, entry in models.items() if isinstance(entry, dict)]

    if not model:
        raise ValueError("--model is required unless --all is set")

    entry = models.get(model)
    if not isinstance(entry, dict):
        raise KeyError(f"STT model not found in catalog: {model}")
    return [(model, entry)]


def _iter_tts_targets(model: str | None, all_models: bool) -> list[tuple[str, dict]]:
    catalog = load_tts_catalog()
    models = catalog.get("models")
    if not isinstance(models, dict):
        raise ValueError("Invalid TTS catalog: missing models mapping")

    if all_models:
        return [(name, entry) for name, entry in models.items() if isinstance(entry, dict)]

    if not model:
        raise ValueError("--model is required unless --all is set")

    entry = models.get(model)
    if not isinstance(entry, dict):
        raise KeyError(f"TTS model not found in catalog: {model}")
    return [(model, entry)]


def main() -> int:
    # Explicit acquisition path is intentionally online-capable.
    # Ensure runtime-forced offline state does not block intentional pulls.
    os.environ["HF_HUB_OFFLINE"] = "0"

    parser = argparse.ArgumentParser(description="Ensure model artifacts are present")
    parser.add_argument("--family", required=True, choices=["stt", "tts"])
    parser.add_argument("--model")
    parser.add_argument("--all", action="store_true")
    parser.add_argument("--verify-only", action="store_true")
    args = parser.parse_args()

    try:
        if args.family == "stt":
            targets = _iter_stt_targets(model=args.model, all_models=args.all)
        else:
            targets = _iter_tts_targets(model=args.model, all_models=args.all)
    except Exception as exc:
        print(f"[FAILED] catalog resolution: {exc}")
        return 1

    failed = False

    for model_name, entry in targets:
        hf_repo_id = entry.get("hf_repo_id")
        local_dir = entry.get("local_dir")

        if not isinstance(hf_repo_id, str) or not hf_repo_id.strip():
            print(f"[FAILED] {model_name}: missing hf_repo_id in catalog")
            failed = True
            continue
        if not isinstance(local_dir, str) or not local_dir.strip():
            print(f"[FAILED] {model_name}: missing local_dir in catalog")
            failed = True
            continue

        if args.verify_only:
            if verify_model(local_dir, family=args.family):
                print(f"[PRESENT] {model_name} → {local_dir}")
            else:
                print(f"[MISSING] {model_name} → {local_dir}")
                failed = True
            continue

        if verify_model(local_dir, family=args.family):
            print(f"[PRESENT] {model_name} → {local_dir}")
            continue

        print(f"[DOWNLOAD] {model_name} → {local_dir}")
        try:
            ensure_model(hf_repo_id=hf_repo_id, local_dir=local_dir, family=args.family)
            print(f"[DONE] {model_name} → {local_dir}")
        except ModelNotAvailableError as exc:
            print(f"[FAILED] {model_name}: {exc}")
            failed = True

    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
