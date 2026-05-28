"""Evidence formatting and citation selection."""
from __future__ import annotations
import re
from typing import Any
from .schemas import Citation

ROLE_PRIORITY = {"primary":0, "interpretation":1, "industry":2, "summary":3, "technical":4, "domain":4, "duplicate":5, "distractor":9, "poisoned":99}

def clean_ws(text: str) -> str:
    return re.sub(r"\s+", " ", text or "").strip()

def compact_evidence(evidence: list[Any], max_chars_per_chunk: int = 900) -> list[dict[str, Any]]:
    out = []
    for ev in evidence:
        quote = clean_ws(getattr(ev, "quote", "") or getattr(ev, "text", ""))
        if len(quote) > max_chars_per_chunk: quote = quote[:max_chars_per_chunk].rstrip()+"..."
        out.append({"rank": ev.rank, "doc_id": ev.doc_id, "chunk_id": ev.chunk_id, "doc_title": ev.doc_title, "doc_role": ev.doc_role, "section_type": ev.section_type, "section_number": ev.section_number, "section_title": ev.section_title, "page_start": ev.page_start, "page_end": ev.page_end, "is_distractor": ev.is_distractor, "is_duplicate": ev.is_duplicate, "is_poisoned": ev.is_poisoned, "score_rerank": ev.score_rerank, "quote": quote})
    return out

def citations_from_evidence(evidence: list[Any], max_citations: int = 3) -> list[Citation]:
    safe = [ev for ev in evidence if not ev.is_poisoned and (ev.doc_role or "").lower() != "poisoned"]
    safe.sort(key=lambda ev: (ROLE_PRIORITY.get((ev.doc_role or "").lower(), 6), ev.rank))
    citations = []
    for ev in safe[:max_citations]:
        quote = clean_ws(ev.quote or ev.text or "")
        if len(quote) > 650: quote = quote[:650].rstrip()+"..."
        citations.append(Citation(doc_id=ev.doc_id, chunk_id=ev.chunk_id, quote=quote, doc_title=ev.doc_title or None, page_start=ev.page_start, page_end=ev.page_end, source_role=ev.doc_role or None))
    return citations

def article5_fallback_summary(quote: str) -> str:
    q = quote.lower(); items = []
    if "subliminal" in q or "manipulative" in q or "deceptive" in q: items.append("subliminal, manipulative or deceptive techniques that materially distort behaviour")
    if "vulnerab" in q: items.append("exploitation of vulnerabilities of persons or groups")
    if "social scoring" in q or "social score" in q: items.append("social scoring practices")
    if "biometric" in q and ("categorisation" in q or "categorization" in q): items.append("certain biometric categorisation practices")
    if "emotion" in q and ("workplace" in q or "education" in q): items.append("emotion recognition in workplace or educational contexts, subject to exceptions")
    if "facial recognition" in q or "scraping" in q: items.append("untargeted scraping of facial images for facial recognition databases")
    if not items: return "Article 5 lists prohibited AI practices; the cited quote provides the exact legal wording."
    return "Article 5 prohibits, among other things, " + "; ".join(items) + "."
