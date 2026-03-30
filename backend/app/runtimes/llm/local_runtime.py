from __future__ import annotations

from pathlib import Path

from backend.app.core.settings import LLAMA_CPP_MODEL_PATH
from backend.app.runtimes.llm.base import LLMBase

try:
    import llama_cpp  # type: ignore  # noqa: F401
except ImportError:  # pragma: no cover - optional dependency
    llama_cpp = None  # type: ignore[assignment]


class LlamaCppLLM(LLMBase):
    def is_available(self) -> bool:
        if not LLAMA_CPP_MODEL_PATH:
            return False
        return Path(LLAMA_CPP_MODEL_PATH).is_file()

    def complete(self, prompt: str) -> str:
        if not self.is_available():
            raise NotImplementedError(
                "LlamaCppLLM: no model loaded — set LLAMA_CPP_MODEL_PATH"
            )
        raise NotImplementedError("LlamaCppLLM inference wiring is deferred")
