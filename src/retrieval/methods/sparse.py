"""Sparse BM25 search."""
from __future__ import annotations
import numpy as np
from src.retrieval.store.index_store import IndexStore
from src.retrieval.utils.text import bm25_tokenize

class BM25Searcher:
    def __init__(self, store: IndexStore) -> None:
        self.store = store

    def search(self, query: str, top_k: int = 50) -> list[tuple[int, float]]:
        scores = self.store.bm25.get_scores(bm25_tokenize(query))
        if len(scores) == 0:
            return []
        k = min(top_k, len(scores))
        idxs = np.argpartition(scores, -k)[-k:]
        idxs = idxs[np.argsort(scores[idxs])[::-1]]
        return [(int(i), float(scores[i])) for i in idxs if float(scores[i]) > 0]
