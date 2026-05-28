"""
Reads retrieval-ready chunks from chunks.jsonl and builds:
  1. Dense vector index with sentence-transformers + FAISS
  2. Sparse BM25 index with rank_bm25
  3. Chunk store used by retriever.py

Input:
  data/processed/chunks_800_120.jsonl

Output directory:
  data/index/
    faiss.index
    bm25.pkl
    chunk_store.jsonl
    index_meta.json

Example:
  python src/retrieval/build_indexes.py \
    --chunks data/processed/chunks_800_120.jsonl \
    --out-dir data/index \
    --embedding-model BAAI/bge-base-en-v1.5 \
    --batch-size 32
"""

from __future__ import annotations

import argparse
import json
import logging
import pickle
import re
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np

log = logging.getLogger("build_indexes")


# ---------------------------------------------------------------------------
# Text normalization / BM25 tokenization
# ---------------------------------------------------------------------------

_TOKEN_RE = re.compile(r"[a-zA-Z0-9]+(?:[-_/][a-zA-Z0-9]+)*")


def bm25_tokenize(text: str) -> list[str]:
    """Tokenizer for legal/compliance text.

    Keeps article numbers, EU identifiers, and legal terms. We intentionally do
    not remove stopwords aggressively, because words such as not, shall, unless,
    except, provider and deployer can be legally meaningful.
    """
    text = (text or "").lower()
    text = text.replace("\xa0", " ").replace("\u202f", " ")
    return _TOKEN_RE.findall(text)


def normalize_embeddings(x: np.ndarray) -> np.ndarray:
    norms = np.linalg.norm(x, axis=1, keepdims=True)
    norms[norms == 0] = 1.0
    return x / norms


# ---------------------------------------------------------------------------
# Loading chunks
# ---------------------------------------------------------------------------


def load_chunks(path: Path, limit: int | None = None, skip_poisoned_from_index: bool = False) -> list[dict[str, Any]]:
    chunks: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            if not line.strip():
                continue
            c = json.loads(line)
            if skip_poisoned_from_index and c.get("is_poisoned"):
                continue
            chunks.append(c)
            if limit and len(chunks) >= limit:
                break
    return chunks


def chunk_text_for_dense(chunk: dict[str, Any]) -> str:
    return chunk.get("embedding_text") or chunk.get("text") or ""


def chunk_text_for_bm25(chunk: dict[str, Any]) -> str:
    return chunk.get("bm25_text") or chunk.get("text") or ""


# ---------------------------------------------------------------------------
# Index builders
# ---------------------------------------------------------------------------


def build_dense_index(chunks: list[dict[str, Any]], model_name: str, batch_size: int, out_dir: Path) -> dict[str, Any]:
    try:
        import faiss  # type: ignore
    except Exception as e:
        raise RuntimeError("faiss is not installed. Install with: pip install faiss-cpu") from e

    try:
        from sentence_transformers import SentenceTransformer
    except Exception as e:
        raise RuntimeError("sentence-transformers is not installed. Install with: pip install sentence-transformers") from e

    log.info("loading embedding model: %s", model_name)
    model = SentenceTransformer(model_name)

    texts = [chunk_text_for_dense(c) for c in chunks]
    log.info("encoding %d chunks batch_size=%d", len(texts), batch_size)
    embeddings = model.encode(
        texts,
        batch_size=batch_size,
        show_progress_bar=True,
        convert_to_numpy=True,
        normalize_embeddings=False,
    ).astype("float32")

    embeddings = normalize_embeddings(embeddings).astype("float32")
    dim = embeddings.shape[1]

    # Cosine similarity = inner product after L2 normalization.
    index = faiss.IndexFlatIP(dim)
    index.add(embeddings)

    faiss_path = out_dir / "faiss.index"
    faiss.write_index(index, str(faiss_path))
    log.info("wrote FAISS index: %s vectors=%d dim=%d", faiss_path, index.ntotal, dim)

    return {
        "faiss_path": str(faiss_path),
        "embedding_model": model_name,
        "embedding_dim": int(dim),
        "vectors": int(index.ntotal),
        "metric": "cosine_via_inner_product_normalized",
    }


def build_bm25_index(chunks: list[dict[str, Any]], out_dir: Path) -> dict[str, Any]:
    try:
        from rank_bm25 import BM25Okapi
    except Exception as e:
        raise RuntimeError("rank_bm25 is not installed. Install with: pip install rank-bm25") from e

    corpus_tokens = [bm25_tokenize(chunk_text_for_bm25(c)) for c in chunks]
    bm25 = BM25Okapi(corpus_tokens)

    bm25_path = out_dir / "bm25.pkl"
    with bm25_path.open("wb") as f:
        pickle.dump({
            "bm25": bm25,
            "tokenizer": "regex_legal_v1",
            "doc_count": len(chunks),
        }, f)

    avg_len = round(sum(len(t) for t in corpus_tokens) / max(1, len(corpus_tokens)), 2)
    log.info("wrote BM25 index: %s docs=%d avg_terms=%.2f", bm25_path, len(chunks), avg_len)

    return {
        "bm25_path": str(bm25_path),
        "tokenizer": "regex_legal_v1",
        "documents": len(chunks),
        "avg_terms_per_chunk": avg_len,
    }


def write_chunk_store(chunks: list[dict[str, Any]], out_dir: Path) -> Path:
    path = out_dir / "chunk_store.jsonl"
    with path.open("w", encoding="utf-8") as f:
        for c in chunks:
            # Store full chunk metadata. retriever.py will use list index == FAISS/BM25 index.
            f.write(json.dumps(c, ensure_ascii=False) + "\n")
    log.info("wrote chunk store: %s chunks=%d", path, len(chunks))
    return path


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def setup_logging(verbose: bool = False) -> None:
    logging.basicConfig(
        format="%(asctime)s | %(levelname)-7s | %(message)s",
        datefmt="%H:%M:%S",
        level=logging.DEBUG if verbose else logging.INFO,
    )


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--chunks", default="data/processed/chunks_800_120.jsonl")
    ap.add_argument("--out-dir", default="data/index")
    ap.add_argument("--embedding-model", default="BAAI/bge-base-en-v1.5")
    ap.add_argument("--batch-size", type=int, default=32)
    ap.add_argument("--limit", type=int, default=None, help="Optional small test build")
    ap.add_argument("--skip-poisoned-from-index", action="store_true", help="Do not index poisoned chunks. Usually keep false for adversarial evaluation.")
    ap.add_argument("--clean", action="store_true", help="Delete output directory before rebuilding")
    ap.add_argument("--verbose", action="store_true")
    args = ap.parse_args()

    setup_logging(args.verbose)

    chunks_path = Path(args.chunks)
    out_dir = Path(args.out_dir)

    if not chunks_path.exists():
        log.error("chunks file not found: %s", chunks_path)
        return 1

    if args.clean and out_dir.exists():
        shutil.rmtree(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    chunks = load_chunks(chunks_path, limit=args.limit, skip_poisoned_from_index=args.skip_poisoned_from_index)
    if not chunks:
        log.error("no chunks loaded from %s", chunks_path)
        return 1

    log.info("loaded chunks=%d from %s", len(chunks), chunks_path)

    by_format: dict[str, int] = {}
    by_role: dict[str, int] = {}
    for c in chunks:
        by_format[c.get("doc_format", "")] = by_format.get(c.get("doc_format", ""), 0) + 1
        by_role[c.get("doc_role", "")] = by_role.get(c.get("doc_role", ""), 0) + 1

    chunk_store_path = write_chunk_store(chunks, out_dir)
    dense_meta = build_dense_index(chunks, args.embedding_model, args.batch_size, out_dir)
    bm25_meta = build_bm25_index(chunks, out_dir)

    meta = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "source_chunks": str(chunks_path),
        "out_dir": str(out_dir),
        "chunk_store_path": str(chunk_store_path),
        "total_chunks": len(chunks),
        "by_format": dict(sorted(by_format.items())),
        "by_role": dict(sorted(by_role.items())),
        "dense": dense_meta,
        "bm25": bm25_meta,
        "notes": {
            "faiss_row_alignment": "FAISS row i and BM25 doc i correspond to line i in chunk_store.jsonl",
            "poisoned_indexing": "Poisoned chunks are indexed unless --skip-poisoned-from-index is used, to support adversarial retrieval evaluation.",
        },
    }

    meta_path = out_dir / "index_meta.json"
    meta_path.write_text(json.dumps(meta, indent=2, ensure_ascii=False), encoding="utf-8")
    log.info("wrote metadata: %s", meta_path)

    log.info("SUMMARY chunks=%d formats=%s roles=%s", len(chunks), by_format, by_role)
    return 0


if __name__ == "__main__":
    sys.exit(main())
