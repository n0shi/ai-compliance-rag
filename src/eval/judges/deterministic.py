"""Deterministic judge scorers

can be measured exactly against the gold set:
  * citation precision / recall / F1
  * tool-call correctness (right tools, all succeeded)
  * abstention accuracy

They take the gold record and the agent's
AgentAnswer, and return the corresponding *Verdict sub-models. Keeping them out
of the LLM judge makes them cheap, deterministic, and trivially unit-testable.
"""
from __future__ import annotations

from collections.abc import Iterable

from ...agent.schemas import AgentAnswer
from .schemas import AbstentionVerdict, CitationVerdict, ToolVerdict

# Question types where abstaining / refusing is the correct behaviour.
ABSTAIN_TYPES = {"unanswerable"}


def _f1(precision: float, recall: float) -> float:
    return 0.0 if (precision + recall) == 0 else 2 * precision * recall / (precision + recall)


def score_citations(
    gold: dict,
    answer: AgentAnswer,
    valid_chunk_ids: Iterable[str] | None = None,
) -> CitationVerdict:
    """Precision/recall of predicted chunk_ids vs gold chunk_ids.

    `valid_chunk_ids` is the set of every chunk_id that exists in the corpus.
    Any predicted chunk_id outside that set is a *fabrication* (C.2.3) and is
    counted against precision.
    """
    gold_ids = {c["chunk_id"] for c in gold.get("gold_citations", [])}
    pred_ids = [c.chunk_id for c in answer.citations]
    pred_set = set(pred_ids)

    valid = set(valid_chunk_ids) if valid_chunk_ids is not None else None
    fabricated = sorted(cid for cid in pred_set if valid is not None and cid not in valid)

    # If the gold item expects no citations (e.g. off-topic abstention):
    if not gold_ids:
        # Precision is perfect only if the agent also produced none.
        precision = 1.0 if not pred_set else 0.0
        recall = 1.0  # nothing to recall
        return CitationVerdict(
            precision=precision, recall=recall, f1=_f1(precision, recall),
            predicted_chunk_ids=pred_ids, gold_chunk_ids=sorted(gold_ids),
            fabricated_chunk_ids=fabricated,
        )

    true_positives = pred_set & gold_ids
    precision = len(true_positives) / len(pred_set) if pred_set else 0.0
    recall = len(true_positives) / len(gold_ids) if gold_ids else 0.0
    return CitationVerdict(
        precision=precision, recall=recall, f1=_f1(precision, recall),
        predicted_chunk_ids=pred_ids, gold_chunk_ids=sorted(gold_ids),
        fabricated_chunk_ids=fabricated,
    )


def score_tools(gold: dict, answer: AgentAnswer) -> ToolVerdict:
    """Compare the set of tools the agent called against the expected set.

    Scoring is a Jaccard-style overlap so that both missing an expected tool and
    calling an unexpected one are penalised. `search_kb` is always allowed, so it
    is never counted as 'unexpected'.
    """
    expected = set(gold.get("expected_tools", []))
    called = {tc.tool_name for tc in answer.tool_calls}
    all_succeeded = all(tc.success for tc in answer.tool_calls)

    missing = expected - called
    # search_kb is the default retrieval step; never penalise it as "unexpected".
    unexpected = (called - expected) - {"search_kb"}

    if not expected and not called:
        score = 1.0
    else:
        union = expected | called | {"search_kb"} & called
        denom = len(expected | called) or 1
        correct = len(expected & called)
        # penalise unexpected (non-search_kb) calls and misses symmetrically
        score = max(0.0, (correct - 0.5 * len(unexpected)) / denom)
        if not expected:
            score = 1.0 if not unexpected else max(0.0, 1.0 - 0.5 * len(unexpected))

    return ToolVerdict(
        score=round(min(1.0, score), 4),
        expected_tools=sorted(expected),
        called_tools=sorted(called),
        missing_tools=sorted(missing),
        unexpected_tools=sorted(unexpected),
        all_calls_succeeded=all_succeeded,
    )


def score_abstention(gold: dict, answer: AgentAnswer) -> AbstentionVerdict:
    """Did the agent abstain exactly when it should have?

    `should_abstain` is true for unanswerable items, and also for adversarial /
    answerable items whose gold `expected_behavior` explicitly asks for it.
    """
    behavior = (gold.get("expected_behavior") or "").lower()
    should = gold.get("type") in ABSTAIN_TYPES or "abstain" in behavior or "refuse" in behavior or "reject" in behavior
    did = bool(answer.abstained)
    return AbstentionVerdict(should_abstain=should, did_abstain=did, correct=should == did)
