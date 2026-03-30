from __future__ import annotations

import httpx

from backend.app.core.settings import OLLAMA_HOST, OLLAMA_MODEL
from backend.app.runtimes.llm.base import LLMBase


class OllamaLLM(LLMBase):
    def is_available(self) -> bool:
        try:
            response = httpx.get(f"{OLLAMA_HOST}/api/tags", timeout=3.0)
            return response.status_code == 200
        except Exception:
            return False

    def complete(self, prompt: str) -> str:
        try:
            response = httpx.post(
                f"{OLLAMA_HOST}/api/generate",
                json={"model": OLLAMA_MODEL, "prompt": prompt, "stream": False},
                timeout=60.0,
            )
            if response.status_code != 200:
                raise RuntimeError
            payload = response.json()
            text = payload.get("response") if isinstance(payload, dict) else None
            if isinstance(text, str):
                return text
            raise RuntimeError
        except Exception as exc:
            raise RuntimeError(f"OllamaLLM: no response from {OLLAMA_HOST}") from exc
