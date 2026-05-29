"""LLM-based judge scorers (faithfulness + relevance).

Wraps an LLMProvider (the SAME abstraction the agent uses) configured with a
DIFFERENT / LARGER model than the system under test, as required by A.6. Output
is parsed via the project's robust JSON parser and validated against the
schemas; on failure we degrade to a neutral score rather than crash a long run.
"""
from __future__ import annotations

from ...agent.json_utils import parse_model_json
from ...providers import ChatMessage, LLMProvider
from .prompts import (
    FAITHFULNESS_SYSTEM,
    RELEVANCE_SYSTEM,
    faithfulness_prompt,
    relevance_prompt,
)
from .schemas import FaithfulnessVerdict, RelevanceVerdict


class LLMJudge:
    """Scores faithfulness and answer relevance with a judge LLM."""

    def __init__(self, provider: LLMProvider, max_tokens: int = 400) -> None:
        self.provider = provider
        self.max_tokens = max_tokens

    @property
    def model(self) -> str:
        return getattr(self.provider, "model", "unknown")

    def _ask_json(self, system: str, user: str) -> dict:
        resp = self.provider.chat(
            [ChatMessage("system", system), ChatMessage("user", user)],
            temperature=0.0, max_tokens=self.max_tokens, json_mode=True,
        )
        return parse_model_json(resp.content)

    def faithfulness(self, question: str, answer: str, citations: list[dict]) -> FaithfulnessVerdict:
        # No citations -> nothing can be grounded. Don't waste a judge call.
        if not citations:
            return FaithfulnessVerdict(
                score=0.0, supported_claims=0, unsupported_claims=0,
                rationale="No citations provided; nothing grounded.",
            )
        try:
            obj = self._ask_json(FAITHFULNESS_SYSTEM, faithfulness_prompt(question, answer, citations))
            return FaithfulnessVerdict.model_validate(obj)
        except Exception as e:  # noqa: BLE001 - degrade gracefully on a bad judge response
            return FaithfulnessVerdict(score=0.5, rationale=f"Judge parse failure ({type(e).__name__}); neutral score.")

    def relevance(self, question: str, answer: str) -> RelevanceVerdict:
        try:
            obj = self._ask_json(RELEVANCE_SYSTEM, relevance_prompt(question, answer))
            return RelevanceVerdict.model_validate(obj)
        except Exception as e:  # noqa: BLE001
            return RelevanceVerdict(score=0.5, rationale=f"Judge parse failure ({type(e).__name__}); neutral score.")
