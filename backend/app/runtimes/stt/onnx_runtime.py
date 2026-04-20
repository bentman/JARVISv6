from __future__ import annotations

import importlib
from pathlib import Path
from typing import Any

from backend.app.models.catalog import get_model_entry
from backend.app.models.manager import ModelNotAvailableError, ensure_model
from backend.app.runtimes.stt.base import STTBase


class OnnxWhisperSTT(STTBase):
    def __init__(self, model_name: str, device: str = "cpu") -> None:
        self.model_name = model_name
        self.device = device
        self._runtime: Any | None = None

    def is_available(self) -> bool:
        try:
            importlib.import_module("onnxruntime")
            importlib.import_module("onnx_asr")
            return True
        except Exception:
            return False

    def _create_runtime(self, model_dir: Path) -> Any:
        try:
            onnx_asr = importlib.import_module("onnx_asr")
        except Exception as exc:
            raise RuntimeError(f"OnnxWhisperSTT: transcription failed ({exc})") from exc

        load_model = getattr(onnx_asr, "load_model", None)
        if not callable(load_model):
            raise RuntimeError("onnx_asr.load_model is unavailable")

        return load_model(
            "whisper",
            path=str(model_dir),
            providers=["CPUExecutionProvider"],
        )

    def _ensure_runtime(self) -> None:
        if self._runtime is not None:
            return

        try:
            importlib.import_module("onnxruntime")
            importlib.import_module("onnx_asr")

            entry = get_model_entry(self.model_name)
            hf_repo_id = entry.get("hf_repo_id")
            local_dir = entry.get("local_dir")
            if not isinstance(hf_repo_id, str) or not hf_repo_id.strip():
                raise RuntimeError(
                    f"catalog missing hf_repo_id for model '{self.model_name}'"
                )
            if not isinstance(local_dir, str) or not local_dir.strip():
                raise RuntimeError(
                    f"catalog missing local_dir for model '{self.model_name}'"
                )

            local_load_error: Exception | None = None
            local_model_dir = Path(local_dir)
            if local_model_dir.exists() and local_model_dir.is_dir():
                try:
                    self._runtime = self._create_runtime(local_model_dir)
                    self.device = "cpu"
                    return
                except Exception as exc:
                    local_load_error = exc

            try:
                resolved_local_dir = ensure_model(
                    hf_repo_id=hf_repo_id,
                    local_dir=local_dir,
                )
            except ModelNotAvailableError as exc:
                if local_load_error is not None:
                    raise RuntimeError(
                        "local model incompatible for onnx-asr "
                        f"({local_load_error}); model materialization failed ({exc})"
                    ) from exc
                raise

            model_root = Path(resolved_local_dir)
            if not model_root.exists() or not model_root.is_dir():
                raise RuntimeError(f"model directory not found: {resolved_local_dir}")

            try:
                self._runtime = self._create_runtime(model_root)
            except Exception as exc:
                if local_load_error is not None:
                    raise RuntimeError(
                        "local model incompatible for onnx-asr "
                        f"({local_load_error}); fallback load failed ({exc})"
                    ) from exc
                raise

            # This runtime is CPU-EP only for 0.0.A.2.
            self.device = "cpu"
        except Exception as exc:
            raise RuntimeError(f"OnnxWhisperSTT: transcription failed ({exc})") from exc

    def _extract_transcript(self, output: Any) -> str:
        if isinstance(output, str):
            return output.strip()

        if isinstance(output, dict):
            for key in ("text", "transcript", "result"):
                value = output.get(key)
                if isinstance(value, str) and value.strip():
                    return value.strip()
            for value in output.values():
                if isinstance(value, str) and value.strip():
                    return value.strip()

        if isinstance(output, (list, tuple)):
            for item in output:
                text = self._extract_transcript(item)
                if text:
                    return text

        tolist = getattr(output, "tolist", None)
        if callable(tolist):
            try:
                return self._extract_transcript(tolist())
            except Exception:
                pass

        raise RuntimeError("unsupported transcript output shape")

    def transcribe(self, audio_path: str) -> str:
        path = Path(audio_path)
        if not path.exists():
            raise RuntimeError(
                f"OnnxWhisperSTT: transcription failed (audio file not found: {audio_path})"
            )

        try:
            self._ensure_runtime()
            if self._runtime is None:
                raise RuntimeError("runtime not loaded")

            recognize = getattr(self._runtime, "recognize", None)
            if not callable(recognize):
                raise RuntimeError("onnx-asr runtime missing recognize()")

            result = recognize(str(path))

            transcript = self._extract_transcript(result)
            if not transcript:
                raise RuntimeError("empty transcript output")
            return transcript
        except Exception as exc:
            if isinstance(exc, RuntimeError) and str(exc).startswith(
                "OnnxWhisperSTT: transcription failed ("
            ):
                raise
            raise RuntimeError(f"OnnxWhisperSTT: transcription failed ({exc})") from exc
