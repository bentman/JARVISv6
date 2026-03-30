from __future__ import annotations

import os


OLLAMA_MODEL: str = os.environ.get("OLLAMA_MODEL", "phi3:mini")
OLLAMA_HOST: str = os.environ.get("OLLAMA_HOST", "http://localhost:11434")
LLAMA_CPP_MODEL_PATH: str | None = os.environ.get("LLAMA_CPP_MODEL_PATH") or None
