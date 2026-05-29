"""Prompts (rubrics) for the LLM-as-a-Judge.
"""
from __future__ import annotations

import json

FAITHFULNESS_SYSTEM = (
    "You are a strict evaluator of an EU AI-Act / GDPR compliance assistant. "
    "Your job is to judge GROUNDEDNESS only: whether each factual claim in the "
    "assistant's answer is supported by the text of the citations it provided. "
    "You do not reward correct-sounding claims that are not backed by a citation. "
    "You never use outside knowledge to fill gaps. Return ONLY one JSON object."
)

RELEVANCE_SYSTEM = (
    "You are a strict evaluator of an EU AI-Act / GDPR compliance assistant. "
    "Your job is to judge ANSWER RELEVANCE only: whether the answer addresses the "
    "specific question that was asked, regardless of whether it is correct. "
    "Return ONLY one JSON object."
)


def faithfulness_prompt(question: str, answer: str, citations: list[dict]) -> str:
    """Build the user message for the faithfulness judge."""
    cite_block = json.dumps(
        [{"chunk_id": c.get("chunk_id"), "quote": c.get("quote")} for c in citations],
        ensure_ascii=False, indent=2,
    )
    return (
        f"QUESTION:\n{question}\n\n"
        f"ASSISTANT ANSWER:\n{answer}\n\n"
        f"CITATIONS (the only evidence you may rely on):\n{cite_block}\n\n"
        "Break the answer into its distinct factual claims. For each claim decide "
        "if it is supported by at least one citation quote above. A claim about a "
        "legal article/number is supported only if a citation quote actually "
        "concerns that article/number.\n\n"
        "Return ONLY this JSON object:\n"
        "{\n"
        '  "supported_claims": <int>,\n'
        '  "unsupported_claims": <int>,\n'
        '  "score": <float 0..1 = supported / (supported + unsupported)>,\n'
        '  "rationale": "<one or two sentences>"\n'
        "}"
    )


def relevance_prompt(question: str, answer: str) -> str:
    """Build the user message for the relevance judge."""
    return (
        f"QUESTION:\n{question}\n\n"
        f"ASSISTANT ANSWER:\n{answer}\n\n"
        "Rate how well the answer addresses the question on a 0..1 scale:\n"
        "  1.0 = directly and fully answers the question\n"
        "  0.5 = partially relevant or addresses only part of it\n"
        "  0.0 = off-topic or does not address the question\n"
        "Note: a deliberate, well-justified refusal/abstention for an out-of-scope "
        "or unanswerable question should score HIGH on relevance (it correctly "
        "responds to the request).\n\n"
        "Return ONLY this JSON object:\n"
        "{\n"
        '  "score": <float 0..1>,\n'
        '  "rationale": "<one sentence>"\n'
        "}"
    )
