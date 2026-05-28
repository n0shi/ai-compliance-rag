from __future__ import annotations
from ..retrieval.cli import main
from ..retrieval.store.index_store import IndexStore
from ..retrieval.pipelines.pipelines import RetrievalPipeline

class HybridRetriever:
    def __init__(self, index_dir: str = "data/index", embedding_model: str | None = None, device: str | None = None) -> None:
        self.store = IndexStore(index_dir, embedding_model=embedding_model, device=device)
        self.index_dir = index_dir
        self.device = device
        self.rerank_model = "BAAI/bge-reranker-base"

    def load_reranker(self, model_name: str = "BAAI/bge-reranker-base") -> None:
        self.rerank_model = model_name
        # Lazy-loaded by RetrievalPipeline when search mode uses reranking.

    def search(self, query: str, top_k: int = 5, dense_k: int = 50, bm25_k: int = 50, rrf_k: int = 60, rerank: bool = True, rerank_k: int = 30, exclude_poisoned: bool = False):
        mode = "hybrid_rerank" if rerank else "hybrid"
        pipe = RetrievalPipeline(self.store, mode=mode, rerank_model=self.rerank_model, device=self.device)
        return pipe.search(query, top_k=top_k, dense_k=dense_k, bm25_k=bm25_k, rrf_k=rrf_k, rerank_k=rerank_k, exclude_poisoned=exclude_poisoned)

if __name__ == "__main__":
    raise SystemExit(main())
