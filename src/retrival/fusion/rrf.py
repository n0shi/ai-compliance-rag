"""Reciprocal Rank Fusion."""
from __future__ import annotations

def reciprocal_rank_fusion(dense: list[tuple[int, float]], sparse: list[tuple[int, float]], rrf_k: int = 60) -> list[tuple[int, dict]]:
    fused: dict[int, dict] = {}
    for rank, (idx, score) in enumerate(dense, start=1):
        item = fused.setdefault(idx, {"score_rrf": 0.0})
        item["score_rrf"] += 1.0 / (rrf_k + rank)
        item["dense_rank"] = rank
        item["score_dense"] = score
    for rank, (idx, score) in enumerate(sparse, start=1):
        item = fused.setdefault(idx, {"score_rrf": 0.0})
        item["score_rrf"] += 1.0 / (rrf_k + rank)
        item["bm25_rank"] = rank
        item["score_bm25"] = score
    return sorted(fused.items(), key=lambda x: x[1]["score_rrf"], reverse=True)
