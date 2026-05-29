"""Ollama provider supporting local daemon and Ollama Cloud.

Local models use http://localhost:11434/api/chat.
Cloud models like gpt-oss:20b-cloud use https://ollama.com/api/chat and
read the key from OLLAMA_API_KEY, adding Authorization: Bearer <key>.
"""
from __future__ import annotations
import json, os, time, urllib.error, urllib.request
from typing import Any
from .base import ChatMessage, LLMResponse

class OllamaProvider:
    provider_name = "ollama"
    def __init__(self, model: str = "llama3.1:8b", base_url: str | None = None, timeout: int = 300, api_key: str | None = None) -> None:
        self.model = model
        self.timeout = timeout
        if base_url is None:
            base_url = "https://ollama.com" if model.endswith("-cloud") else "http://localhost:11434"
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key or os.getenv("OLLAMA_API_KEY")

    @property
    def is_cloud(self) -> bool:
        return "ollama.com" in self.base_url or self.model.endswith("-cloud")

    def _headers(self) -> dict[str, str]:
        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        elif self.is_cloud:
            raise RuntimeError('Ollama Cloud requires an API key. Run: export OLLAMA_API_KEY="your_key_here"')
        return headers

    def _post_json(self, path: str, payload: dict[str, Any]) -> dict[str, Any]:
        req = urllib.request.Request(f"{self.base_url}{path}", data=json.dumps(payload).encode("utf-8"), headers=self._headers(), method="POST")
        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as response:
                return json.loads(response.read().decode("utf-8"))
        except urllib.error.HTTPError as e:
            try: body = e.read().decode("utf-8", errors="replace")
            except Exception: body = ""
            if e.code in {401, 403}:
                raise RuntimeError(f"Ollama authentication failed. Check OLLAMA_API_KEY and model access. HTTP {e.code}: {body}") from e
            raise RuntimeError(f"Ollama API error HTTP {e.code}: {body}") from e
        except urllib.error.URLError as e:
            raise RuntimeError(f"Could not connect to Ollama at {self.base_url}. Local: check ollama serve. Cloud: check internet/key. Original: {e}") from e

    def chat(self, messages: list[ChatMessage], temperature: float = 0.0, max_tokens: int | None = None, json_mode: bool = False) -> LLMResponse:
        started = time.perf_counter()
        payload: dict[str, Any] = {
            "model": self.model,
            "messages": [{"role": m.role, "content": m.content} for m in messages if m.role in {"system", "user", "assistant"}],
            "stream": False,
            "options": {"temperature": temperature},
        }
        if max_tokens is not None:
            payload["options"]["num_predict"] = max_tokens
        if json_mode:
            payload["format"] = "json"
        raw = self._post_json("/api/chat", payload)
        latency = round(time.perf_counter() - started, 3)
        content = raw.get("message", {}).get("content", "")
        in_tok, out_tok = raw.get("prompt_eval_count"), raw.get("eval_count")
        total = in_tok + out_tok if isinstance(in_tok, int) and isinstance(out_tok, int) else None
        return LLMResponse(content=content, model=self.model, provider=self.provider_name, input_tokens=in_tok, output_tokens=out_tok, total_tokens=total, latency_seconds=latency, raw=raw)
