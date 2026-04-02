from __future__ import annotations

import os
import sys
from typing import Any
from pathlib import Path

from backend.app.models.catalog import get_model_entry
from backend.app.models.manager import ModelNotAvailableError, ensure_model
from backend.app.runtimes.stt.base import STTBase


_DLL_DIR_HANDLES: list[Any] = []
_DLL_DIRS_INITIALIZED = False


def _configure_windows_cuda_dll_dirs() -> None:
    global _DLL_DIRS_INITIALIZED
    if _DLL_DIRS_INITIALIZED:
        return

    if os.name != "nt" or not hasattr(os, "add_dll_directory"):
        _DLL_DIRS_INITIALIZED = True
        return

    candidate_dirs: list[Path] = []

    cuda_path = os.environ.get("CUDA_PATH")
    if cuda_path:
        candidate_dirs.append(Path(cuda_path) / "bin")

    venv = Path(sys.prefix)
    candidate_dirs.extend(
        [
            venv / "Lib" / "site-packages" / "nvidia" / "cublas" / "bin",
            venv / "Lib" / "site-packages" / "nvidia" / "cudnn" / "bin",
            venv / "Lib" / "site-packages" / "nvidia" / "cuda_runtime" / "bin",
        ]
    )

    seen: set[str] = set()
    for dll_dir in candidate_dirs:
        resolved = dll_dir.resolve()
        key = str(resolved).lower()
        if key in seen or not resolved.exists():
            continue
        seen.add(key)
        try:
            handle = os.add_dll_directory(str(resolved))
            _DLL_DIR_HANDLES.append(handle)
        except Exception:
            continue

    _DLL_DIRS_INITIALIZED = True


def _is_cuda_dll_error(exc: BaseException) -> bool:
    """Return True when the exception indicates a CUDA runtime DLL load failure."""
    msg = str(exc).lower()
    return "cublas64_12.dll" in msg and ("not found" in msg or "cannot be loaded" in msg)


class FasterWhisperSTT(STTBase):
    def __init__(self, model_name: str, device: str = "cpu") -> None:
        self.model_name = model_name
        self.device = device
        self._model: Any | None = None

    def is_available(self) -> bool:
        try:
            from faster_whisper import WhisperModel  # type: ignore  # noqa: F401

            return True
        except Exception:
            return False

    def _ensure_model(self) -> None:
        if self._model is not None:
            return
        try:
            from faster_whisper import WhisperModel  # type: ignore

            entry = get_model_entry(self.model_name)
            hf_repo_id = entry.get("hf_repo_id")
            local_dir = entry.get("local_dir")
            if not isinstance(hf_repo_id, str) or not hf_repo_id.strip():
                raise RuntimeError(
                    f"FasterWhisperSTT: catalog missing hf_repo_id for model '{self.model_name}'"
                )
            if not isinstance(local_dir, str) or not local_dir.strip():
                raise RuntimeError(
                    f"FasterWhisperSTT: catalog missing local_dir for model '{self.model_name}'"
                )

            resolved_local_dir = ensure_model(hf_repo_id=hf_repo_id, local_dir=local_dir)
            requested_device = self.device.lower()
            if requested_device == "cuda":
                _configure_windows_cuda_dll_dirs()
                try:
                    self._model = WhisperModel(resolved_local_dir, device="cuda")
                except Exception as cuda_exc:
                    message = str(cuda_exc).lower()
                    if "cublas64_12.dll" in message and (
                        "not found" in message or "cannot be loaded" in message
                    ):
                        print(
                            "[STT DEVICE] CUDA unavailable (cublas64_12.dll not loadable) — falling back to cpu"
                        )
                        self._model = WhisperModel(resolved_local_dir, device="cpu")
                    else:
                        raise RuntimeError(
                            f"FasterWhisperSTT: transcription failed ({cuda_exc})"
                        ) from cuda_exc
            else:
                self._model = WhisperModel(resolved_local_dir, device=self.device)
        except ModelNotAvailableError as exc:
            raise RuntimeError(f"FasterWhisperSTT: transcription failed ({exc})") from exc
        except Exception as exc:
            raise RuntimeError(f"FasterWhisperSTT: transcription failed ({exc})") from exc

    def transcribe(self, audio_path: str) -> str:
        path = Path(audio_path)
        if not path.exists():
            raise RuntimeError(f"FasterWhisperSTT: audio file not found: {audio_path}")

        self._ensure_model()
        if self._model is None:
            raise RuntimeError("FasterWhisperSTT: transcription failed (model not loaded)")
        try:
            segments, _info = self._model.transcribe(str(path), language="en")
            transcript = " ".join(segment.text.strip() for segment in segments).strip()
            return transcript
        except Exception as exc:
            if _is_cuda_dll_error(exc) and self.device.lower() == "cuda":
                print(
                    "[STT DEVICE] CUDA unavailable (cublas64_12.dll not loadable) — falling back to cpu"
                )
                try:
                    from faster_whisper import WhisperModel  # type: ignore

                    entry = get_model_entry(self.model_name)
                    local_dir = entry.get("local_dir", "")
                    self._model = WhisperModel(local_dir, device="cpu")
                    self.device = "cpu"
                    segments, _info = self._model.transcribe(str(path), language="en")
                    transcript = " ".join(segment.text.strip() for segment in segments).strip()
                    return transcript
                except Exception as cpu_exc:
                    raise RuntimeError(
                        f"FasterWhisperSTT: transcription failed on cpu fallback ({cpu_exc})"
                    ) from cpu_exc
            raise RuntimeError(f"FasterWhisperSTT: transcription failed ({exc})") from exc
