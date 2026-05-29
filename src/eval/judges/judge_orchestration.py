"""Judge orchestrator.

Combines the LLM-scored dimensions (faithfulness, relevance) with the
deterministic ones (citations, tools, abstention) into a single Verdict per
question

The composite weighting is type-aware:
  * For items where abstaining is correct (unanswerable / refuse-injection),
    abstention dominates and citation recall is not penalised.
  * For answerable / multi-hop / distractor items, faithfulness and citations
    matter most.
"""
from __future__ import annotations

import json
from functools import lru_cache

from ...agent.schemas import AgentAnswer
from .deterministic import score_abstention, score_citations, score_tools
from .llm_judge import LLMJudge
from .schemas import Verdict


@lru_cache(maxsize=4)
def load_valid_chunk_ids(chunk_store_path: str = "data/index/chunk_store.jsonl") -> frozenset[str]:
    """Every chunk_id that exists in the corpus (for fabrication detection)."""
    ids = set()
    with open(chunk_store_path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                ids.add(json.loads(line)["chunk_id"])
    return frozenset(ids)


# Composite weights per question family. Keys must sum to 1.0 within a family.
_WEIGHTS_ANSWERABLE = {"faithfulness": 0.40, "relevance": 0.20, "citation_f1": 0.30, "tools": 0.10}
_WEIGHTS_ABSTAIN = {"abstention": 0.70, "relevance": 0.30}


class ComplianceJudge:
    """Top-level judge used by the eval runner."""

    def __init__(self, llm_judge: LLMJudge, chunk_store_path: str = "data/index/chunk_store.jsonl") -> None:
        self.llm = llm_judge
        self.valid_chunk_ids = load_valid_chunk_ids(chunk_store_path)

    def judge(self, gold: dict, answer: AgentAnswer, latency_seconds: float | None = None,
              tokens: tuple[int | None, int | None, int | None] = (None, None, None)) -> Verdict:
        qtype = gold.get("type", "answerable")
        citations_as_dicts = [c.model_dump() for c in answer.citations]

        # Deterministic dimensions (cheap, always computed).
        cit = score_citations(gold, answer, valid_chunk_ids=self.valid_chunk_ids)
        tools = score_tools(gold, answer)
        abst = score_abstention(gold, answer)

        # LLM dimensions. Relevance is always meaningful; faithfulness only when
        # the agent actually answered (an abstention has no claims to ground).
        rel = self.llm.relevance(gold["question"], answer.answer)
        faith = None
        if not answer.abstained:
            faith = self.llm.faithfulness(gold["question"], answer.answer, citations_as_dicts)

        composite = self._composite(qtype, faith, rel, cit, tools, abst)

        in_tok, out_tok, total = tokens
        return Verdict(
            question_id=gold["id"], question_type=qtype,
            faithfulness=faith, relevance=rel, citations=cit, tools=tools, abstention=abst,
            latency_seconds=latency_seconds, input_tokens=in_tok, output_tokens=out_tok, total_tokens=total,
            composite_score=composite, judge_model=self.llm.model,
        )

    @staticmethod
    def _composite(qtype, faith, rel, cit, tools, abst) -> float:
        # Hard penalty applies regardless of branch: fabricating a chunk_id that
        # does not exist in the corpus is a critical failure (C.2.3) and zeroes
        # the item even on an abstain-expected question.
        if cit and cit.fabricated_chunk_ids:
            return 0.0

        if abst.should_abstain:
            w = _WEIGHTS_ABSTAIN
            return round(
                w["abstention"] * (1.0 if abst.correct else 0.0)
                + w["relevance"] * (rel.score if rel else 0.0),
                4,
            )
        w = _WEIGHTS_ANSWERABLE
        score = (
            w["faithfulness"] * (faith.score if faith else 0.0)
            + w["relevance"] * (rel.score if rel else 0.0)
            + w["citation_f1"] * (cit.f1 if cit else 0.0)
            + w["tools"] * (tools.score if tools else 0.0)
        )
        return round(score, 4)
