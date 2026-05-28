"""Text helpers for retrieval."""
from __future__ import annotations
import re
_TOKEN_RE = re.compile(r"[a-zA-Z0-9]+(?:[-_/][a-zA-Z0-9]+)*")

def bm25_tokenize(text: str) -> list[str]:
    return [m.group(0).lower() for m in _TOKEN_RE.finditer(text or "")]

def bge_query_text(query: str) -> str:
    return f"Represent this sentence for searching relevant passages: {query}"

def clean_ws(text: str) -> str:
    return re.sub(r"\s+", " ", text or "").strip()

def make_quote(text: str, max_chars: int = 450) -> str:
    q = clean_ws(text)
    return q if len(q) <= max_chars else q[:max_chars].rstrip() + "..."
