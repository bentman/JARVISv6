from __future__ import annotations

from pathlib import Path

from huggingface_hub import snapshot_download


class ModelNotAvailableError(Exception):
    pass


def verify_model(local_dir: str, family: str = "stt") -> bool:
    path = Path(local_dir)
    if not path.exists() or not path.is_dir():
        return False
    if family == "stt":
        # CTranslate2 / faster-whisper artifact set — tokenizer.json is a transformers
        # artifact and is NOT present in Systran/faster-whisper-* repos. Do not include it.
        required_files = (
            "model.bin",
            "config.json",
            "vocabulary.json",
        )
    elif family == "tts":
        required_files = ("kokoro-v1_0.pth",)
    else:
        raise ValueError(f"Unsupported model family for verify_model: {family}")

    return all((path / name).exists() for name in required_files)


def download_model(hf_repo_id: str, local_dir: str, offline_only: bool = False) -> str:
    target = Path(local_dir)
    target.mkdir(parents=True, exist_ok=True)
    try:
        snapshot_download(
            repo_id=hf_repo_id,
            local_dir=str(target),
            local_files_only=offline_only,
        )
    except Exception as exc:
        raise ModelNotAvailableError(
            f"download failed for repo '{hf_repo_id}' to '{local_dir}': {exc}"
        ) from exc
    return str(target)


def ensure_model(
    hf_repo_id: str,
    local_dir: str,
    family: str = "stt",
    offline_only: bool = False,
) -> str:
    if verify_model(local_dir, family=family):
        return local_dir
    download_model(hf_repo_id=hf_repo_id, local_dir=local_dir, offline_only=offline_only)
    if not verify_model(local_dir, family=family):
        raise ModelNotAvailableError(
            f"verify failed after download for repo '{hf_repo_id}' at '{local_dir}'"
        )
    return local_dir
