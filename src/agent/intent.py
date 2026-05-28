"""Simple intent detectors for tool use."""
from __future__ import annotations
import re
from typing import Any

def extract_money_amount_eur(text: str) -> float | None:
    t = text.lower().replace(",", " ")
    m = re.search(r"(?P<num>\d+(?:\.\d+)?)\s*(?P<scale>billion|million|bn|m)?\s*(?:eur|euro|€)", t)
    if not m: return None
    value = float(m.group("num")); scale = m.group("scale")
    if scale in {"billion", "bn"}: value *= 1_000_000_000
    elif scale in {"million", "m"}: value *= 1_000_000
    return value

def detect_penalty_request(question: str) -> dict[str, Any] | None:
    q = question.lower()
    if not any(w in q for w in ["penalty", "fine", "turnover", "administrative fine"]): return None
    law = "GDPR" if "gdpr" in q else "AI Act"
    if law == "AI Act":
        violation_type = "prohibited_practice" if ("prohibited" in q or "article 5" in q) else "misleading_information" if ("misleading" in q or "incorrect" in q or "incomplete" in q) else "non_compliance"
    else:
        violation_type = "upper_tier" if ("upper" in q or "article 83(5)" in q or "consent" in q or "data subject" in q) else "lower_tier"
    return {"law": law, "violation_type": violation_type, "annual_turnover_eur": extract_money_amount_eur(question)}

def detect_deadline_request(question: str) -> str | None:
    q = question.lower()
    if not any(w in q for w in ["when", "deadline", "start applying", "apply", "application"]): return None
    if "prohibited" in q or "article 5" in q: return "prohibited_practices"
    if "gpai" in q or "general-purpose" in q or "general purpose" in q: return "gpai_obligations"
    if "high-risk" in q or "high risk" in q: return "high_risk_obligations"
    if "general application" in q or "fully apply" in q or "full application" in q: return "general_application"
    if "entry into force" in q: return "entry_into_force"
    return None
