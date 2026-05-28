"""Input/output guardrails."""
from __future__ import annotations
import re
from .schemas import AgentAnswer, GuardrailDecision

LEGAL_TOPIC_RE = re.compile(r"\b(ai act|artificial intelligence act|gdpr|dsa|data protection|privacy|high-risk|prohibited|article\s+\d+|annex|provider|deployer|conformity assessment|transparency|automated decision|profiling|nist|risk management|compliance|regulation|eu law|european union|fine|penalty|deadline|turnover|gpai)\b", re.I)
PERSONAL_DATA_RE = re.compile(r"\b(password|api key|secret key|private key|token|credit card|social security|passport|dump emails|leak personal|personal data of)\b", re.I)
PROMPT_INJECTION_RE = re.compile(r"\b(ignore previous instructions|ignore all previous|system prompt|developer message|reveal your instructions|jailbreak|act as dan|bypass|do not follow)\b", re.I)

def check_input(question: str) -> GuardrailDecision:
    q = question or ""
    if PROMPT_INJECTION_RE.search(q): return GuardrailDecision(allowed=False, category="prompt_injection", reason="Prompt-injection or jailbreak language detected.")
    if PERSONAL_DATA_RE.search(q): return GuardrailDecision(allowed=False, category="personal_data", reason="Request appears to ask for secrets or personal data leakage.")
    if not LEGAL_TOPIC_RE.search(q): return GuardrailDecision(allowed=False, category="off_topic", reason="Question is outside AI Act / GDPR / AI compliance scope.")
    return GuardrailDecision(allowed=True, category="ok", reason="Input is in scope.")

def evidence_reliability(evidence) -> float:
    if not evidence: return 0.0
    top = evidence[:5]; score = 0.0
    for i, ev in enumerate(top):
        rw = 1/(i+1); role = (ev.doc_role or "").lower()
        rs = 1.0 if role == "primary" else 0.8 if role == "interpretation" else 0.55 if role in {"industry","summary","technical","domain"} else 0.35 if role == "duplicate" else 0.15 if role == "distractor" else 0.0 if role == "poisoned" else 0.4
        if ev.is_poisoned: rs = 0.0
        elif ev.is_distractor: rs = min(rs, 0.15)
        if ev.score_rerank is not None: rs = min(1.0, rs + max(0.0, min(float(ev.score_rerank), 1.0)) * 0.15)
        score += rw * rs
    return round(score / sum(1/(i+1) for i in range(len(top))), 4)

def should_abstain(evidence, threshold: float = 0.45) -> tuple[bool, float]:
    rel = evidence_reliability(evidence); return rel < threshold, rel

def check_output(answer: AgentAnswer, citations_required: bool = True) -> GuardrailDecision:
    if citations_required and not answer.abstained and not answer.citations: return GuardrailDecision(allowed=False, category="missing_citations", reason="Non-abstained answer has no citations.")
    if answer.confidence < 0.35 and not answer.abstained: return GuardrailDecision(allowed=False, category="low_confidence", reason="Low-confidence answer must abstain.")
    for c in answer.citations:
        if (c.source_role or "").lower() == "poisoned": return GuardrailDecision(allowed=False, category="missing_citations", reason="Poisoned chunks cannot be cited.")
    return GuardrailDecision(allowed=True, category="ok", reason="Output passed guardrails.")
