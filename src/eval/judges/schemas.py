"""Structured verdict schemas for the LLM-as-a-Judge system.
"""
from __future__ import annotations

from pydantic import BaseModel, Field


class FaithfulnessVerdict(BaseModel):
    """Are the answer's claims grounded in the cited evidence?"""
    score: float = Field(..., ge=0.0, le=1.0, description="Fraction of claims supported by citations")
    supported_claims: int = 0
    unsupported_claims: int = 0
    rationale: str = ""


class RelevanceVerdict(BaseModel):
    """Does the answer actually address the question that was asked?"""
    score: float = Field(..., ge=0.0, le=1.0)
    rationale: str = ""


class CitationVerdict(BaseModel):
    """Precision/recall of cited chunks vs. the gold citations (deterministic)."""
    precision: float = Field(..., ge=0.0, le=1.0)
    recall: float = Field(..., ge=0.0, le=1.0)
    f1: float = Field(..., ge=0.0, le=1.0)
    predicted_chunk_ids: list[str] = Field(default_factory=list)
    gold_chunk_ids: list[str] = Field(default_factory=list)
    # A fabricated chunk_id is one the agent emitted that does not exist in the corpus.
    fabricated_chunk_ids: list[str] = Field(default_factory=list)


class ToolVerdict(BaseModel):
    """Did the agent call the tools the gold item expects (correct set + success)?"""
    score: float = Field(..., ge=0.0, le=1.0)
    expected_tools: list[str] = Field(default_factory=list)
    called_tools: list[str] = Field(default_factory=list)
    missing_tools: list[str] = Field(default_factory=list)
    unexpected_tools: list[str] = Field(default_factory=list)
    all_calls_succeeded: bool = True


class AbstentionVerdict(BaseModel):
    """Did the agent abstain exactly when it should have?"""
    should_abstain: bool
    did_abstain: bool
    correct: bool


class Verdict(BaseModel):
    """Full per-question judgement combining LLM + deterministic dimensions."""
    question_id: str
    question_type: str

    faithfulness: FaithfulnessVerdict | None = None
    relevance: RelevanceVerdict | None = None
    citations: CitationVerdict | None = None
    tools: ToolVerdict | None = None
    abstention: AbstentionVerdict | None = None

    # Cost / latency (A.6 requires reporting these, not just quality).
    latency_seconds: float | None = None
    input_tokens: int | None = None
    output_tokens: int | None = None
    total_tokens: int | None = None

    # A single 0..1 roll-up used for ranking systems / Pareto plots (C.4).
    composite_score: float | None = None

    # Bookkeeping for the >=20% manual-review requirement.
    judge_model: str = ""
    notes: str = ""

    def to_row(self) -> dict:
        """Flatten to a single dict row for CSV / tables / pandas."""
        return {
            "question_id": self.question_id,
            "type": self.question_type,
            "faithfulness": self.faithfulness.score if self.faithfulness else None,
            "relevance": self.relevance.score if self.relevance else None,
            "citation_precision": self.citations.precision if self.citations else None,
            "citation_recall": self.citations.recall if self.citations else None,
            "citation_f1": self.citations.f1 if self.citations else None,
            "fabricated_citations": len(self.citations.fabricated_chunk_ids) if self.citations else 0,
            "tool_score": self.tools.score if self.tools else None,
            "abstention_correct": self.abstention.correct if self.abstention else None,
            "latency_seconds": self.latency_seconds,
            "total_tokens": self.total_tokens,
            "composite_score": self.composite_score,
            "judge_model": self.judge_model,
        }
