"""Retrieval data models."""
from __future__ import annotations
from dataclasses import dataclass, asdict
from typing import Any

@dataclass
class RetrievalResult:
    rank: int
    chunk_id: str
    doc_id: str
    doc_title: str = ""
    doc_url: str = ""
    doc_format: str = ""
    doc_role: str = ""
    section_type: str = ""
    section_number: str | None = None
    section_title: str = ""
    page_start: int | None = None
    page_end: int | None = None
    score_rrf: float | None = None
    score_dense: float | None = None
    score_bm25: float | None = None
    score_rerank: float | None = None
    dense_rank: int | None = None
    bm25_rank: int | None = None
    is_distractor: bool = False
    is_duplicate: bool = False
    is_poisoned: bool = False
    quote: str = ""
    text: str = ""
    def to_dict(self) -> dict[str, Any]:
        return asdict(self)
