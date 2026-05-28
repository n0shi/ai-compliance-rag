"""Cross-encoder reranker."""
from __future__ import annotations
from typing import Any
from src.retrieval.utils.text import clean_ws

class CrossEncoderReranker:
    def __init__(self, model_name: str = "BAAI/bge-reranker-base", device: str | None = None) -> None:
        from sentence_transformers import CrossEncoder
        kwargs = {"device": device} if device else {}
        self.model_name = model_name
        self.model = CrossEncoder(model_name, **kwargs)

    def rerank(self, query: str, candidates: list[tuple[int, dict[str, Any]]], chunks: list[dict[str, Any]], top_k: int | None = None) -> list[tuple[int, dict[str, Any]]]:
        pairs = []
        for idx, info in candidates:
            c = chunks[idx]
            header = f"{c.get('doc_title','')} {c.get('section_title','')} Article {c.get('section_number','')}"
            pairs.append([query, clean_ws(header + "\n" + (c.get("text") or c.get("quote") or ""))])
        scores = self.model.predict(pairs)
        enriched = []
        for (idx, info), score in zip(candidates, scores):
            info = dict(info)
            info["score_rerank"] = float(score)
            enriched.append((idx, info))
        enriched.sort(key=lambda x: x[1].get("score_rerank", 0.0), reverse=True)
        return enriched[:top_k] if top_k else enriched
