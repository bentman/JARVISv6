from __future__ import annotations

from backend.app.runtimes.llm.base import LLMBase


def get_response(prompt: str, llm: LLMBase) -> str:
    response = llm.complete(prompt)
    if not response or not response.strip():
        raise RuntimeError("responder: empty response from LLM")
    return response
