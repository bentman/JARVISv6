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
        # STT supports both CTranslate2 (faster-whisper) and ONNX Whisper
        # artifact layouts. tokenizer.json is a transformers artifact and is
        # not required here.
        has_vocab_file = (path / "vocabulary.json").exists() or (path / "vocab.json").exists()
        has_config = (path / "config.json").exists()

        has_ctranslate2_artifacts = (path / "model.bin").exists() and has_config and has_vocab_file
        if has_ctranslate2_artifacts:
            return True

        def _has_whisper_onnx_export(base_dir: Path) -> bool:
            has_encoder = (base_dir / "encoder_model.onnx").exists()
            has_decoder_merged = (base_dir / "decoder_model_merged.onnx").exists()
            has_decoder = (base_dir / "decoder_model.onnx").exists()
            has_decoder_with_past = (base_dir / "decoder_with_past_model.onnx").exists()
            return bool(has_encoder and (has_decoder_merged or (has_decoder and has_decoder_with_past)))

        onnx_dir = path / "onnx"
        has_processor_assets = (
            (path / "preprocessor_config.json").exists()
            and (path / "tokenizer_config.json").exists()
            and (path / "tokenizer.json").exists()
        )
        has_onnx_artifacts = (
            has_processor_assets
            and has_config
            and has_vocab_file
            and (
                (onnx_dir.exists() and onnx_dir.is_dir() and _has_whisper_onnx_export(onnx_dir))
                or _has_whisper_onnx_export(path)
            )
        )
        if has_onnx_artifacts:
            return True

        return False
    elif family == "tts":
        if (path / "kokoro-v1_0.pth").exists():
            return True

        has_onnx_file = any(path.glob("*.onnx")) or any((path / "onnx").glob("*.onnx"))
        has_voice_pack = any(path.glob("voices*.bin")) or any((path / "voices").glob("*.bin"))
        if has_onnx_file and has_voice_pack:
            return True

        return False
    else:
        raise ValueError(f"Unsupported model family for verify_model: {family}")


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
