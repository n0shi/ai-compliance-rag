"""Common LLM provider interface."""
from __future__ import annotations
from dataclasses import dataclass
from typing import Any, Literal, Protocol

Role = Literal["system", "user", "assistant", "tool"]

@dataclass
class ChatMessage:
    role: Role
    content: str

@dataclass
class LLMResponse:
    content: str
    model: str
    provider: str
    input_tokens: int | None = None
    output_tokens: int | None = None
    total_tokens: int | None = None
    latency_seconds: float | None = None
    raw: dict[str, Any] | None = None

class LLMProvider(Protocol):
    provider_name: str
    model: str
    def chat(self, messages: list[ChatMessage], temperature: float = 0.0, max_tokens: int | None = None, json_mode: bool = False) -> LLMResponse: ...
