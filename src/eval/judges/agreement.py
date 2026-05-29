"""Aggregation of verdicts and judge<->human agreement.
"""
from __future__ import annotations

import json
import math
import random
from collections import defaultdict
from collections.abc import Sequence

from .schemas import Verdict

# Composite >= this counts as the judge calling the answer "acceptable".
ACCEPT_THRESHOLD = 0.6


def aggregate(verdicts: Sequence[Verdict]) -> dict:
    """Mean of each metric overall and broken down by question type."""
    def _mean(xs):
        xs = [x for x in xs if x is not None]
        return round(sum(xs) / len(xs), 4) if xs else None

    rows = [v.to_row() for v in verdicts]
    metrics = ["faithfulness", "relevance", "citation_precision", "citation_recall",
               "citation_f1", "tool_score", "abstention_correct", "composite_score",
               "latency_seconds", "total_tokens"]

    overall = {m: _mean([r[m] for r in rows]) for m in metrics}
    overall["fabricated_citations_total"] = sum(r["fabricated_citations"] for r in rows)
    overall["n"] = len(rows)

    by_type: dict[str, dict] = {}
    grouped: dict[str, list] = defaultdict(list)
    for r in rows:
        grouped[r["type"]].append(r)
    for t, group in grouped.items():
        by_type[t] = {m: _mean([r[m] for r in group]) for m in metrics}
        by_type[t]["n"] = len(group)
        by_type[t]["fabricated_citations_total"] = sum(r["fabricated_citations"] for r in group)

    return {"overall": overall, "by_type": by_type}


def sample_for_review(verdicts: Sequence[Verdict], fraction: float = 0.2, seed: int = 13) -> list[str]:
    """Pick >= `fraction` of question_ids (stratified by type) for manual review."""
    by_type: dict[str, list[str]] = defaultdict(list)
    for v in verdicts:
        by_type[v.question_type].append(v.question_id)
    picked: list[str] = []
    rng = random.Random(seed)
    for ids in by_type.values():
        k = max(1, math.ceil(len(ids) * fraction))
        picked.extend(rng.sample(ids, min(k, len(ids))))
    return sorted(picked)


def cohens_kappa(judge: list[int], human: list[int]) -> float:
    """Cohen's kappa for two binary label lists (acceptable=1 / not=0)."""
    assert len(judge) == len(human) and judge, "need equal, non-empty label lists"
    n = len(judge)
    agree = sum(1 for a, b in zip(judge, human) if a == b) / n
    pj1 = sum(judge) / n
    ph1 = sum(human) / n
    expected = pj1 * ph1 + (1 - pj1) * (1 - ph1)
    return round((agree - expected) / (1 - expected), 4) if expected != 1.0 else 1.0


def agreement_report(verdicts: Sequence[Verdict], human_review_path: str) -> dict:
    """Compare judge 'acceptable' decisions to a human review JSON.

    human_review_path is a JSON dict: {question_id: {"acceptable": 0|1}, ...}
    Only the overlap between reviewed ids and verdicts is scored.
    """
    with open(human_review_path, encoding="utf-8") as f:
        human = json.load(f)

    by_id = {v.question_id: v for v in verdicts}
    judge_labels, human_labels, compared = [], [], []
    for qid, rec in human.items():
        if qid not in by_id:
            continue
        v = by_id[qid]
        j = 1 if (v.composite_score or 0.0) >= ACCEPT_THRESHOLD else 0
        h = int(rec.get("acceptable", 0))
        judge_labels.append(j)
        human_labels.append(h)
        compared.append(qid)

    if not compared:
        return {"reviewed": 0, "note": "No overlap between human review and verdicts."}

    raw_agree = round(sum(1 for a, b in zip(judge_labels, human_labels) if a == b) / len(compared), 4)
    return {
        "reviewed": len(compared),
        "reviewed_fraction": round(len(compared) / len(verdicts), 4),
        "raw_agreement": raw_agree,
        "cohens_kappa": cohens_kappa(judge_labels, human_labels),
        "compared_ids": compared,
    }
