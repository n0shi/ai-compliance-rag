"""Dense FAISS search."""
from __future__ import annotations
import numpy as np
from src.retrieval.store.index_store import IndexStore
from src.retrieval.utils.text import bge_query_text
from src.retrieval.utils.vector import normalize_vector

class DenseSearcher:
    def __init__(self, store: IndexStore) -> None:
        self.store = store

    def search(self, query: str, top_k: int = 50) -> list[tuple[int, float]]:
        q = bge_query_text(query) if "bge" in self.store.embedding_model_name.lower() else query
        emb = self.store.encoder.encode([q], convert_to_numpy=True, normalize_embeddings=False).astype("float32")
        emb[0] = normalize_vector(emb[0])
        scores, ids = self.store.faiss_index.search(emb, top_k)
        out: list[tuple[int, float]] = []
        for idx, score in zip(ids[0], scores[0]):
            if int(idx) >= 0:
                out.append((int(idx), float(score)))
        return out
