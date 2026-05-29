"""IndexStore loads all retrieval artifacts and models in one place."""
from __future__ import annotations
import json, pickle
from pathlib import Path
from typing import Any

class IndexStore:
    def __init__(self, index_dir: str = "data/index", embedding_model: str | None = None, device: str | None = None) -> None:
        self.index_dir = Path(index_dir)
        self.meta = self._load_json(self.index_dir / "index_meta.json")
        self.chunks = self._load_chunks(self.index_dir / "chunk_store.jsonl")
        self.embedding_model_name = embedding_model or self.meta.get("embedding_model") or self.meta.get("dense", {}).get("embedding_model") or "BAAI/bge-base-en-v1.5"
        self.device = device
        self._faiss = None
        self._faiss_index = None
        self._bm25_payload = None
        self._encoder = None

    @staticmethod
    def _load_json(path: Path) -> dict[str, Any]:
        return json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}

    @staticmethod
    def _load_chunks(path: Path) -> list[dict[str, Any]]:
        with path.open("r", encoding="utf-8") as f:
            return [json.loads(line) for line in f if line.strip()]

    @property
    def faiss_index(self):
        if self._faiss_index is None:
            import faiss
            self._faiss = faiss
            self._faiss_index = faiss.read_index(str(self.index_dir / "faiss.index"))
            if self._faiss_index.ntotal != len(self.chunks):
                raise ValueError(f"FAISS vectors ({self._faiss_index.ntotal}) != chunks ({len(self.chunks)})")
        return self._faiss_index

    @property
    def bm25(self):
        if self._bm25_payload is None:
            with (self.index_dir / "bm25.pkl").open("rb") as f:
                self._bm25_payload = pickle.load(f)
        payload = self._bm25_payload
        return payload["bm25"] if isinstance(payload, dict) and "bm25" in payload else payload

    @property
    def encoder(self):
        if self._encoder is None:
            from sentence_transformers import SentenceTransformer
            kwargs = {"device": self.device} if self.device else {}
            self._encoder = SentenceTransformer(self.embedding_model_name, **kwargs)
        return self._encoder
