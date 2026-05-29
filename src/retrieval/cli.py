"""Retrieval CLI."""
from __future__ import annotations
import argparse, json, time
from ..retrieval.store.index_store import IndexStore
from ..retrieval.pipelines.pipelines import RetrievalPipeline

def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--query", required=True)
    ap.add_argument("--index-dir", default="data/index")
    ap.add_argument("--mode", choices=["bm25", "dense", "hybrid", "hybrid_rerank"], default="hybrid_rerank")
    ap.add_argument("--top-k", type=int, default=5)
    ap.add_argument("--dense-k", type=int, default=50)
    ap.add_argument("--bm25-k", type=int, default=50)
    ap.add_argument("--rrf-k", type=int, default=60)
    ap.add_argument("--rerank-k", type=int, default=30)
    ap.add_argument("--embedding-model", default=None)
    ap.add_argument("--rerank-model", default="BAAI/bge-reranker-base")
    ap.add_argument("--device", default=None)
    ap.add_argument("--exclude-poisoned", action="store_true")
    args = ap.parse_args()
    started = time.perf_counter()
    store = IndexStore(args.index_dir, embedding_model=args.embedding_model, device=args.device)
    pipe = RetrievalPipeline(store, mode=args.mode, rerank_model=args.rerank_model, device=args.device)
    results = pipe.search(args.query, top_k=args.top_k, dense_k=args.dense_k, bm25_k=args.bm25_k, rrf_k=args.rrf_k, rerank_k=args.rerank_k, exclude_poisoned=args.exclude_poisoned)
    payload = {"query": args.query, "mode": args.mode, "latency_seconds": round(time.perf_counter()-started,3), "results": [r.to_dict() for r in results]}
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0
if __name__ == "__main__":
    raise SystemExit(main())
