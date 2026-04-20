from __future__ import annotations

import importlib
from pathlib import Path
import tempfile
from typing import Any
import wave

from backend.app.models.catalog import get_tts_model_entry
from backend.app.models.manager import ModelNotAvailableError, ensure_model
from backend.app.runtimes.tts.base import TTSBase


class OnnxKokoroTTSRuntime(TTSBase):
    def __init__(
        self,
        model_name: str,
        voice: str | None = None,
        device: str = "cpu",
    ) -> None:
        self.model_name = model_name
        self.voice = voice or "bf_isabella"
        self.device = device
        self._engine: Any | None = None

    def is_available(self) -> bool:
        try:
            importlib.import_module("kokoro_onnx")
            return True
        except Exception:
            return False

    def _ensure_engine(self) -> None:
        if self._engine is not None:
            return

        try:
            module = importlib.import_module("kokoro_onnx")

            entry = get_tts_model_entry(self.model_name)
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

            try:
                resolved_local_dir = ensure_model(
                    hf_repo_id=hf_repo_id,
                    local_dir=local_dir,
                    family="tts",
                )
            except ModelNotAvailableError:
                resolved_local_dir = local_dir

            model_root = Path(resolved_local_dir)
            if not model_root.exists() or not model_root.is_dir():
                raise RuntimeError(f"model directory not found: {resolved_local_dir}")

            model_path = self._resolve_onnx_model_path(model_root)
            voices_path = self._resolve_voices_path(model_root)

            kokoro_cls = getattr(module, "Kokoro", None)
            if not callable(kokoro_cls):
                raise RuntimeError("kokoro_onnx.Kokoro is unavailable")

            engine: Any | None = None
            constructor_candidates = [
                {"model_path": str(model_path), "voices_path": str(voices_path)},
            ]
            for kwargs in constructor_candidates:
                try:
                    engine = kokoro_cls(**kwargs)
                    break
                except TypeError:
                    continue
                except Exception:
                    continue

            if engine is None:
                try:
                    engine = kokoro_cls(str(model_path), str(voices_path))
                except Exception as exc:
                    raise RuntimeError(
                        f"unable to initialize kokoro_onnx engine ({exc})"
                    ) from exc

            self._engine = engine
            # 0.0.A.4 constrains this runtime to CPU-EP selection.
            self.device = "cpu"
        except Exception as exc:
            raise RuntimeError(f"OnnxKokoroTTSRuntime: synthesis failed ({exc})") from exc

    def _resolve_onnx_model_path(self, model_root: Path) -> Path:
        onnx_dir = model_root / "onnx"
        preferred = [
            onnx_dir / "model.onnx",
            onnx_dir / "model_fp16.onnx",
            onnx_dir / "model_q8f16.onnx",
            onnx_dir / "model_uint8f16.onnx",
            model_root / "model.onnx",
        ]
        for candidate in preferred:
            if candidate.exists() and candidate.is_file():
                return candidate

        if onnx_dir.exists() and onnx_dir.is_dir():
            discovered = sorted(onnx_dir.glob("*.onnx"))
            if discovered:
                return discovered[0]

        discovered = sorted(model_root.glob("*.onnx"))
        if discovered:
            return discovered[0]

        raise RuntimeError(f"no .onnx model file found in: {model_root}")

    def _resolve_voices_path(self, model_root: Path) -> Path:
        direct_candidates = [
            model_root / "voices.npz",
            model_root / "voices.npy",
            model_root / "voices.bin",
            model_root / "voices-v1.0.bin",
        ]
        for candidate in direct_candidates:
            if candidate.exists() and candidate.is_file():
                return candidate

        voices_dir = model_root / "voices"
        if voices_dir.exists() and voices_dir.is_dir():
            return self._materialize_voices_pack(voices_dir)

        raise RuntimeError(
            "voices pack not found; expected a file (voices*.bin/voices*.npz) "
            f"or a voices directory at: {model_root}"
        )

    def _materialize_voices_pack(self, voices_dir: Path) -> Path:
        try:
            import numpy as np  # type: ignore
        except Exception as exc:
            raise RuntimeError(f"audio runtime unavailable ({exc})") from exc

        voice_bins = sorted(path for path in voices_dir.glob("*.bin") if path.is_file())
        if not voice_bins:
            raise RuntimeError(f"no voice bins found in: {voices_dir}")

        cache_dir = Path(tempfile.gettempdir()) / "jarvis" / "kokoro_voices"
        cache_dir.mkdir(parents=True, exist_ok=True)
        voices_pack = cache_dir / f"{self.model_name}.npz"

        newest_source_mtime = max(path.stat().st_mtime for path in voice_bins)
        if voices_pack.exists() and voices_pack.is_file():
            try:
                if voices_pack.stat().st_mtime >= newest_source_mtime:
                    return voices_pack
            except Exception:
                pass

        voice_map: dict[str, Any] = {}
        for voice_file in voice_bins:
            raw = np.fromfile(str(voice_file), dtype=np.float32)
            if raw.size == 0:
                raise RuntimeError(f"voice file empty: {voice_file}")
            if raw.size % 256 != 0:
                raise RuntimeError(
                    f"voice file incompatible shape (expected multiple of 256): {voice_file}"
                )
            voice_map[voice_file.stem] = raw.reshape((-1, 256))

        temp_pack = voices_pack.with_suffix(".tmp.npz")
        np.savez(str(temp_pack), **voice_map)
        temp_pack.replace(voices_pack)

        return voices_pack

    def _synthesize_with_onnx(self, text: str) -> tuple[Any, int]:
        try:
            import numpy as np  # type: ignore
        except Exception as exc:
            raise RuntimeError(f"audio runtime unavailable ({exc})") from exc

        if self._engine is None:
            raise RuntimeError("engine not initialized")

        session = getattr(self._engine, "sess", None)
        if session is None or not callable(getattr(session, "run", None)):
            raise RuntimeError("onnx session unavailable")

        tokenizer = getattr(self._engine, "tokenizer", None)
        if tokenizer is None:
            raise RuntimeError("tokenizer unavailable")

        phonemize = getattr(tokenizer, "phonemize", None)
        tokenize = getattr(tokenizer, "tokenize", None)
        if not callable(phonemize) or not callable(tokenize):
            raise RuntimeError("tokenizer contract unavailable")

        get_voice_style = getattr(self._engine, "get_voice_style", None)
        if not callable(get_voice_style):
            raise RuntimeError("voice style lookup unavailable")

        try:
            voice_style = get_voice_style(self.voice)
        except Exception as exc:
            raise RuntimeError(f"voice style unavailable ({exc})") from exc

        voice_matrix = np.asarray(voice_style, dtype=np.float32)
        if voice_matrix.ndim == 3 and voice_matrix.shape[1] == 1:
            voice_matrix = voice_matrix[:, 0, :]
        elif voice_matrix.ndim == 1:
            if voice_matrix.size % 256 != 0:
                raise RuntimeError("voice style shape unsupported")
            voice_matrix = voice_matrix.reshape((-1, 256))
        elif voice_matrix.ndim != 2:
            raise RuntimeError("voice style shape unsupported")

        if voice_matrix.shape[1] != 256:
            raise RuntimeError(
                f"voice style width incompatible (expected 256, got {voice_matrix.shape[1]})"
            )

        phonemes = phonemize(text, "en-us")
        if not isinstance(phonemes, str) or not phonemes.strip():
            raise RuntimeError("phonemization returned empty output")

        split_phonemes = getattr(self._engine, "_split_phonemes", None)
        raw_chunks: Any
        if callable(split_phonemes):
            raw_chunks = split_phonemes(phonemes)
        else:
            raw_chunks = [phonemes]

        if isinstance(raw_chunks, str):
            chunks = [raw_chunks]
        elif isinstance(raw_chunks, (list, tuple)):
            chunks = [chunk for chunk in raw_chunks if isinstance(chunk, str) and chunk.strip()]
        else:
            chunks = [phonemes]

        audio_chunks: list[Any] = []
        for chunk in chunks:
            token_ids = np.asarray(tokenize(chunk), dtype=np.int64)
            if token_ids.ndim != 1 or token_ids.size == 0:
                continue

            style_index = min(int(token_ids.size), int(voice_matrix.shape[0]) - 1)
            style = np.asarray(voice_matrix[style_index], dtype=np.float32).reshape(1, 256)
            input_ids = np.concatenate(([0], token_ids, [0])).astype(np.int64).reshape(1, -1)
            speed = np.asarray([1.0], dtype=np.float32)

            try:
                outputs = session.run(
                    None,
                    {
                        "input_ids": input_ids,
                        "style": style,
                        "speed": speed,
                    },
                )
            except Exception as exc:
                raise RuntimeError(f"onnx inference failed ({exc})") from exc

            if not outputs:
                raise RuntimeError("onnx inference returned no outputs")

            audio = np.asarray(outputs[0], dtype=np.float32).squeeze()
            if audio.size == 0:
                continue
            audio_chunks.append(audio)

        if not audio_chunks:
            raise RuntimeError("synthesis produced empty audio")

        if len(audio_chunks) == 1:
            return audio_chunks[0], 24000
        return np.concatenate(audio_chunks), 24000

    def _extract_audio_and_sample_rate(self, payload: Any) -> tuple[Any, int]:
        sample_rate = 24000

        if isinstance(payload, tuple):
            if len(payload) >= 2:
                audio = payload[0]
                try:
                    sample_rate = int(payload[1])
                except Exception:
                    sample_rate = 24000
                return audio, sample_rate
            if len(payload) == 1:
                return payload[0], sample_rate

        if isinstance(payload, dict):
            if "audio" in payload:
                audio = payload["audio"]
                try:
                    sample_rate = int(payload.get("sample_rate", 24000))
                except Exception:
                    sample_rate = 24000
                return audio, sample_rate

        if payload is not None:
            return payload, sample_rate

        raise RuntimeError("audio payload not found")

    def _write_pcm16_wav(self, output_path: Path, audio: Any, sample_rate: int) -> None:
        try:
            import numpy as np  # type: ignore
        except Exception as exc:
            raise RuntimeError(f"OnnxKokoroTTSRuntime: synthesis failed ({exc})") from exc

        audio_arr = np.asarray(audio)
        if audio_arr.size == 0:
            raise RuntimeError("OnnxKokoroTTSRuntime: synthesis failed (empty audio payload)")

        if audio_arr.ndim == 1:
            channels = 1
        elif audio_arr.ndim == 2:
            channels = int(audio_arr.shape[1])
            if channels <= 0:
                raise RuntimeError(
                    "OnnxKokoroTTSRuntime: synthesis failed (invalid channel count)"
                )
        else:
            raise RuntimeError("OnnxKokoroTTSRuntime: synthesis failed (unsupported audio shape)")

        if np.issubdtype(audio_arr.dtype, np.floating):
            audio_i16 = (np.clip(audio_arr, -1.0, 1.0) * 32767.0).astype(np.int16)
        elif np.issubdtype(audio_arr.dtype, np.integer):
            audio_i16 = np.clip(audio_arr, -32768, 32767).astype(np.int16)
        else:
            raise RuntimeError("OnnxKokoroTTSRuntime: synthesis failed (unsupported audio dtype)")

        with wave.open(str(output_path), "wb") as wav_file:
            wav_file.setnchannels(channels)
            wav_file.setsampwidth(2)
            wav_file.setframerate(int(sample_rate))
            wav_file.writeframes(audio_i16.tobytes())

    def synthesize(self, text: str, output_path: str) -> str:
        if not isinstance(text, str) or not text.strip():
            raise RuntimeError("OnnxKokoroTTSRuntime: synthesis failed (empty text)")

        out_path = Path(output_path)
        out_path.parent.mkdir(parents=True, exist_ok=True)

        try:
            self._ensure_engine()
            if self._engine is None:
                raise RuntimeError("engine not initialized")
            audio, sample_rate = self._synthesize_with_onnx(text)
            self._write_pcm16_wav(out_path, audio, int(sample_rate))
            return str(out_path)
        except Exception as exc:
            if isinstance(exc, RuntimeError) and str(exc).startswith(
                "OnnxKokoroTTSRuntime: synthesis failed ("
            ):
                raise
            raise RuntimeError(f"OnnxKokoroTTSRuntime: synthesis failed ({exc})") from exc