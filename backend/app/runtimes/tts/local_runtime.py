from __future__ import annotations

from pathlib import Path
from typing import Any

from backend.app.models.catalog import get_tts_model_entry
from backend.app.models.manager import ModelNotAvailableError, ensure_model
from backend.app.runtimes.tts.base import TTSBase


def _is_cuda_runtime_error(exc: BaseException) -> bool:
    msg = str(exc).lower()
    if "cuda requested but not available" in msg:
        return True
    if "torch not compiled with cuda enabled" in msg:
        return True
    if "cuda" in msg and "not available" in msg:
        return True
    return any(token in msg for token in ("cublas", "cudnn", "cuda", "cudart")) and (
        "not found" in msg or "cannot be loaded" in msg or "failed" in msg
    )


class KokoroTTSRuntime(TTSBase):
    def __init__(
        self,
        model_name: str = "kokoro-v1.0",
        voice: str = "af_bella",
        device: str = "cpu",
    ) -> None:
        self.model_name = model_name
        self.voice = voice
        self.device = device
        self._pipeline: Any | None = None

    def is_available(self) -> bool:
        try:
            from kokoro import KPipeline  # type: ignore  # noqa: F401

            return True
        except Exception:
            return False

    def _resolve_local_assets(self, local_dir: str) -> tuple[str, str]:
        local_path = Path(local_dir)
        if not local_path.exists() or not local_path.is_dir():
            raise RuntimeError(
                f"KokoroTTSRuntime: local model directory not found: {local_dir}"
            )

        config_candidates = sorted(
            path for path in local_path.iterdir() if path.is_file() and path.suffix == ".json"
        )
        model_candidates = sorted(
            path for path in local_path.iterdir() if path.is_file() and path.suffix == ".pth"
        )

        if len(config_candidates) != 1:
            raise RuntimeError(
                "KokoroTTSRuntime: unable to resolve local config asset "
                f"in {local_dir} (found {len(config_candidates)}: {[p.name for p in config_candidates]})"
            )
        if len(model_candidates) != 1:
            raise RuntimeError(
                "KokoroTTSRuntime: unable to resolve local model asset "
                f"in {local_dir} (found {len(model_candidates)}: {[p.name for p in model_candidates]})"
            )

        return str(config_candidates[0]), str(model_candidates[0])

    def _build_pipeline(self, hf_repo_id: str, local_dir: str, device: str) -> Any:
        from kokoro import KPipeline  # type: ignore
        from kokoro.model import KModel  # type: ignore

        config_path, model_path = self._resolve_local_assets(local_dir)

        model = KModel(
            repo_id=hf_repo_id,
            config=config_path,
            model=model_path,
        ).to(device).eval()

        return KPipeline(lang_code="a", repo_id=hf_repo_id, model=model, device=device)

    def _ensure_pipeline(self) -> None:
        if self._pipeline is not None:
            return
        try:
            entry = get_tts_model_entry(self.model_name)
            hf_repo_id = entry.get("hf_repo_id")
            local_dir = entry.get("local_dir")

            if not isinstance(hf_repo_id, str) or not hf_repo_id.strip():
                raise RuntimeError(
                    f"KokoroTTSRuntime: catalog missing hf_repo_id for model '{self.model_name}'"
                )
            if not isinstance(local_dir, str) or not local_dir.strip():
                raise RuntimeError(
                    f"KokoroTTSRuntime: catalog missing local_dir for model '{self.model_name}'"
                )

            resolved_local_dir = ensure_model(
                hf_repo_id=hf_repo_id,
                local_dir=local_dir,
                family="tts",
            )
            if not Path(resolved_local_dir).exists():
                raise RuntimeError(
                    f"KokoroTTSRuntime: ensured model directory not found: {resolved_local_dir}"
                )

            if self.device.lower() == "cuda":
                try:
                    self._pipeline = self._build_pipeline(hf_repo_id, resolved_local_dir, "cuda")
                except Exception as cuda_exc:
                    if _is_cuda_runtime_error(cuda_exc):
                        print("[TTS DEVICE] CUDA unavailable — falling back to cpu")
                        self._pipeline = self._build_pipeline(hf_repo_id, resolved_local_dir, "cpu")
                        self.device = "cpu"
                    else:
                        raise RuntimeError(
                            f"KokoroTTSRuntime: synthesis failed ({cuda_exc})"
                        ) from cuda_exc
            else:
                self._pipeline = self._build_pipeline(hf_repo_id, resolved_local_dir, self.device)
        except ModelNotAvailableError as exc:
            raise RuntimeError(f"KokoroTTSRuntime: synthesis failed ({exc})") from exc
        except Exception as exc:
            raise RuntimeError(f"KokoroTTSRuntime: synthesis failed ({exc})") from exc

    def _extract_audio(self, result: Any) -> Any:
        try:
            import numpy as np
        except Exception:  # pragma: no cover
            np = None  # type: ignore

        if isinstance(result, dict) and "audio" in result:
            return result["audio"]
        if hasattr(result, "audio"):
            return getattr(result, "audio")
        if isinstance(result, tuple) and len(result) >= 3:
            return result[2]
        if np is not None and isinstance(result, np.ndarray):
            return result

        if hasattr(result, "__iter__") and not isinstance(result, (str, bytes, dict)):
            chunks: list[Any] = []
            for item in result:
                if isinstance(item, dict) and "audio" in item:
                    chunks.append(item["audio"])
                elif hasattr(item, "audio"):
                    chunks.append(getattr(item, "audio"))
                elif isinstance(item, tuple) and len(item) >= 3:
                    chunks.append(item[2])
            if chunks:
                if np is not None:
                    return np.concatenate(chunks)
                return chunks[0]

        raise RuntimeError("KokoroTTSRuntime: synthesis failed (audio payload not found)")

    def synthesize(self, text: str, output_path: str) -> str:
        if not isinstance(text, str) or not text.strip():
            raise RuntimeError("KokoroTTSRuntime: synthesis failed (empty text)")

        out_path = Path(output_path)
        out_path.parent.mkdir(parents=True, exist_ok=True)

        self._ensure_pipeline()
        if self._pipeline is None:
            raise RuntimeError("KokoroTTSRuntime: synthesis failed (pipeline not initialized)")

        try:
            import soundfile as sf

            result = self._pipeline(text=text, voice=self.voice)
            audio = self._extract_audio(result)
            sf.write(str(out_path), audio, 24000)
            return str(out_path)
        except Exception as exc:
            raise RuntimeError(f"KokoroTTSRuntime: synthesis failed ({exc})") from exc
