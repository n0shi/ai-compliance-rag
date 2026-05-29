"""End-to-end evaluation runner (A.6 + Part B comparison support).

Runs the compliance agent over the gold set, judges every answer with a
LARGER/DIFFERENT judge model, and writes:
  * per-question verdicts (JSONL),
  * aggregate metrics by type and overall (JSON),
  * a stratified >=20% manual-review template (JSON),
  * a human<->judge agreement report when a filled review file is supplied.

Usage:
    python -m src.eval.runners.run_judge_eval \
        --gold data/gold_set.json \
        --agent-model llama3.1:8b \
        --judge-model gpt-oss:20b-cloud \
        --out reports/eval

The agent model and judge model MUST differ (A.6). The runner enforces this.
"""
from __future__ import annotations

import argparse
import json
import time
from pathlib import Path

from ...agent.agent import ComplianceAgent
from ...providers import create_provider
from ..judges.llm_judge import LLMJudge
from ..judges.schemas import  Verdict
from ..judges.judge_orchestration import ComplianceJudge
from ..judges.agreement import aggregate, agreement_report, sample_for_review
def load_gold(path: str) -> list[dict]:
    data = json.load(open(path, encoding="utf-8"))
    return data["questions"] if isinstance(data, dict) and "questions" in data else data


def run(args: argparse.Namespace) -> int:
    if args.agent_model == args.judge_model and args.provider == args.judge_provider:
        raise SystemExit("Judge model must differ from the agent model.")

    gold = load_gold(args.gold)
    if args.limit:
        gold = gold[: args.limit]

    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)

    agent = ComplianceAgent(
        provider_name=args.provider, model=args.agent_model,
        index_dir=args.index_dir, retrieval_mode=args.retrieval_mode,
        abstention_threshold=args.abstention_threshold,
    )
    judge = ComplianceJudge(
        LLMJudge(create_provider(args.judge_provider, model=args.judge_model)),
        chunk_store_path=str(Path(args.index_dir) / "chunk_store.jsonl"),
    )

    verdicts: list[Verdict] = []
    verdicts_path = out_dir / "verdicts.jsonl"
    with verdicts_path.open("w", encoding="utf-8") as vf:
        for i, g in enumerate(gold, 1):
            t0 = time.perf_counter()
            ans = agent.answer(g["question"])
            latency = round(time.perf_counter() - t0, 3)
            # pull token usage from the last LLM tool observation if present
            tokens = (None, None, None)
            v = judge.judge(g, ans, latency_seconds=latency, tokens=tokens)
            verdicts.append(v)
            vf.write(v.model_dump_json() + "\n")
            print(f"[{i}/{len(gold)}] {g['id']:32s} type={g['type']:12s} "
                  f"composite={v.composite_score} abst={ans.abstained}")

    agg = aggregate(verdicts)
    (out_dir / "aggregate.json").write_text(json.dumps(agg, ensure_ascii=False, indent=2), encoding="utf-8")

    review_ids = sample_for_review(verdicts, fraction=args.review_fraction)
    review_template = {qid: {"acceptable": None, "comment": ""} for qid in review_ids}
    (out_dir / "manual_review_template.json").write_text(
        json.dumps(review_template, ensure_ascii=False, indent=2), encoding="utf-8")

    result = {"aggregate": agg, "n_questions": len(verdicts),
              "review_sample_size": len(review_ids),
              "review_fraction": round(len(review_ids) / len(verdicts), 4)}

    if args.human_review and Path(args.human_review).exists():
        result["agreement"] = agreement_report(verdicts, args.human_review)

    (out_dir / "summary.json").write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print("\n=== AGGREGATE (overall) ===")
    print(json.dumps(agg["overall"], ensure_ascii=False, indent=2))
    print(f"\nWrote: {verdicts_path}, aggregate.json, manual_review_template.json, summary.json")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description="LLM-as-a-Judge evaluation over the gold set.")
    ap.add_argument("--gold", default="data/gold_set.json")
    ap.add_argument("--index-dir", default="data/index")
    ap.add_argument("--provider", default="ollama")
    ap.add_argument("--agent-model", default="llama3.1:8b")
    ap.add_argument("--judge-provider", default="ollama")
    ap.add_argument("--judge-model", default="gpt-oss:20b-cloud")
    ap.add_argument("--retrieval-mode", choices=["bm25", "dense", "hybrid", "hybrid_rerank"], default="hybrid_rerank")
    ap.add_argument("--abstention-threshold", type=float, default=0.45)
    ap.add_argument("--review-fraction", type=float, default=0.2)
    ap.add_argument("--human-review", default=None, help="Path to a filled manual review JSON for agreement.")
    ap.add_argument("--limit", type=int, default=None, help="Only run the first N questions (debugging).")
    ap.add_argument("--out", default="reports/eval")
    return run(ap.parse_args())


if __name__ == "__main__":
    raise SystemExit(main())
