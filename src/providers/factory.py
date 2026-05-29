"""Provider factory."""
from __future__ import annotations
from .base import LLMProvider
from .ollama_provider import OllamaProvider

def create_provider(provider: str = "ollama", model: str = "llama3.1:8b", base_url: str | None = None, timeout: int = 300, api_key: str | None = None) -> LLMProvider:
    if provider.strip().lower() == "ollama":
        return OllamaProvider(model=model, base_url=base_url, timeout=timeout, api_key=api_key)
    raise ValueError(f"Unsupported provider: {provider}. Available providers: ollama")
