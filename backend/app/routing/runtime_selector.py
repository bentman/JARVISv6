from __future__ import annotations

from backend.app.core.capabilities import FullCapabilityReport
from backend.app.core.settings import OLLAMA_HOST
from backend.app.runtimes.llm.base import LLMBase
from backend.app.runtimes.llm.local_runtime import LlamaCppLLM
from backend.app.runtimes.llm.ollama_runtime import OllamaLLM


def select_llm_runtime() -> LLMBase:
    local_runtime = LlamaCppLLM()
    if local_runtime.is_available():
        return local_runtime

    ollama_runtime = OllamaLLM()
    if ollama_runtime.is_available():
        return ollama_runtime

    raise RuntimeError(
        "No LLM runtime available. Checked: LlamaCppLLM "
        "(LLAMA_CPP_MODEL_PATH not set or file missing), "
        f"OllamaLLM (Ollama not reachable at {OLLAMA_HOST})"
    )


def select_llm_runtime_for_report(report: FullCapabilityReport | None = None) -> LLMBase:
    """Report-aware compatibility surface for future readiness-aware LLM routing."""

    _ = report
    return select_llm_runtime()
