"""Composable retrieval pipelines for ablation testing."""
from __future__ import annotations
from ...retrieval.store.index_store import IndexStore
from ...retrieval.methods.dense import DenseSearcher
from ...retrieval.methods.sparse import BM25Searcher
from ...retrieval.methods.rerank import CrossEncoderReranker
from ...retrieval.fusion.rrf import reciprocal_rank_fusion
from ...retrieval.pipelines.result_builder import build_results
from ...retrieval.schemas import RetrievalResult

class RetrievalPipeline:
    def __init__(self, store: IndexStore, mode: str = "hybrid_rerank", rerank_model: str = "BAAI/bge-reranker-base", device: str | None = None) -> None:
        self.store = store
        self.mode = mode
        self.dense = DenseSearcher(store)
        self.sparse = BM25Searcher(store)
        self.rerank_model = rerank_model
        self.device = device
        self._reranker: CrossEncoderReranker | None = None

    @property
    def reranker(self) -> CrossEncoderReranker:
        if self._reranker is None:
            self._reranker = CrossEncoderReranker(self.rerank_model, device=self.device)
        return self._reranker

    def search(self, query: str, top_k: int = 5, dense_k: int = 50, bm25_k: int = 50, rrf_k: int = 60, rerank_k: int = 30, exclude_poisoned: bool = False) -> list[RetrievalResult]:
        mode = self.mode
        if mode == "bm25":
            sparse = self.sparse.search(query, bm25_k)
            candidates = [(idx, {"score_bm25": score, "bm25_rank": rank}) for rank, (idx, score) in enumerate(sparse, start=1)]
        elif mode == "dense":
            dense = self.dense.search(query, dense_k)
            candidates = [(idx, {"score_dense": score, "dense_rank": rank}) for rank, (idx, score) in enumerate(dense, start=1)]
        elif mode in {"hybrid", "hybrid_rerank"}:
            dense = self.dense.search(query, dense_k)
            sparse = self.sparse.search(query, bm25_k)
            candidates = reciprocal_rank_fusion(dense, sparse, rrf_k=rrf_k)
            if mode == "hybrid_rerank":
                candidates = self.reranker.rerank(query, candidates[:rerank_k], self.store.chunks)
        else:
            raise ValueError(f"Unknown retrieval mode: {mode}. Use bm25, dense, hybrid, hybrid_rerank")

        if exclude_poisoned:
            candidates = [(idx, info) for idx, info in candidates if not self.store.chunks[idx].get("is_poisoned", False)]
        return build_results(candidates, self.store.chunks, top_k=top_k)
