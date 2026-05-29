"""Build public RetrievalResult objects from internal candidates."""
from __future__ import annotations
from ...retrieval.schemas import RetrievalResult
from ...retrieval.utils.text import make_quote

def build_results(candidates: list[tuple[int, dict]], chunks: list[dict], top_k: int = 5) -> list[RetrievalResult]:
    results: list[RetrievalResult] = []
    for rank, (idx, info) in enumerate(candidates[:top_k], start=1):
        c = chunks[idx]
        results.append(RetrievalResult(
            rank=rank,
            chunk_id=c.get("chunk_id", ""),
            doc_id=c.get("doc_id", ""),
            doc_title=c.get("doc_title", ""),
            doc_url=c.get("doc_url", ""),
            doc_format=c.get("doc_format", ""),
            doc_role=c.get("doc_role", ""),
            section_type=c.get("section_type", ""),
            section_number=c.get("section_number"),
            section_title=c.get("section_title", ""),
            page_start=c.get("page_start"),
            page_end=c.get("page_end"),
            score_rrf=info.get("score_rrf"),
            score_dense=info.get("score_dense"),
            score_bm25=info.get("score_bm25"),
            score_rerank=info.get("score_rerank"),
            dense_rank=info.get("dense_rank"),
            bm25_rank=info.get("bm25_rank"),
            is_distractor=bool(c.get("is_distractor", False)),
            is_duplicate=bool(c.get("is_duplicate", False)),
            is_poisoned=bool(c.get("is_poisoned", False)),
            quote=make_quote(c.get("text") or c.get("quote") or ""),
            text=c.get("text", ""),
        ))
    return results
