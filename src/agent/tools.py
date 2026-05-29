"""Agent tools: KB search, calculators, external lookup."""
from __future__ import annotations
import json, re, time, urllib.parse, urllib.request
from calendar import monthrange
from datetime import date, datetime
from typing import Any
from .schemas import DeadlineCalculation, PenaltyCalculation, ToolCall
from ..retrieval.store.index_store import IndexStore
from ..retrieval.pipelines.pipelines import RetrievalPipeline

# Heavy objects (FAISS index, embedding encoder, cross-encoder reranker) are
# expensive to load and must not be rebuilt per question. We cache the
# IndexStore per index_dir (the index is the same regardless of retrieval mode)
# and the pipeline per (index_dir, mode). This both avoids reloading model
# weights on every call and prevents the Windows page-file exhaustion that
# happens when many torch models are loaded in one process.
_STORE_CACHE: dict[str, IndexStore] = {}
_PIPELINE_CACHE: dict[tuple[str, str], RetrievalPipeline] = {}


def _get_store(index_dir: str) -> IndexStore:
    if index_dir not in _STORE_CACHE:
        _STORE_CACHE[index_dir] = IndexStore(index_dir)
    return _STORE_CACHE[index_dir]


def _get_pipeline(index_dir: str, mode: str) -> RetrievalPipeline:
    key = (index_dir, mode)
    if key not in _PIPELINE_CACHE:
        _PIPELINE_CACHE[key] = RetrievalPipeline(_get_store(index_dir), mode=mode)
    return _PIPELINE_CACHE[key]


def clear_retrieval_cache() -> None:
    """Drop cached store/pipelines (e.g. between ablation runs that swap models)."""
    _STORE_CACHE.clear()
    _PIPELINE_CACHE.clear()

def search_kb(query: str, index_dir: str = "data/index", mode: str = "hybrid_rerank", top_k: int = 5, dense_k: int = 50, bm25_k: int = 50, rrf_k: int = 60, rerank_k: int = 30, exclude_poisoned: bool = False):
    started = time.perf_counter()
    pipe = _get_pipeline(index_dir, mode)
    evidence = pipe.search(query, top_k=top_k, dense_k=dense_k, bm25_k=bm25_k, rrf_k=rrf_k, rerank_k=rerank_k, exclude_poisoned=exclude_poisoned)
    call = ToolCall(tool_name="search_kb", arguments={"query": query, "index_dir": index_dir, "mode": mode, "top_k": top_k}, success=True, observation_summary=f"Retrieved {len(evidence)} chunks in {round(time.perf_counter()-started,3)}s")
    return evidence, call

AI_ACT = {"prohibited_practice": (35_000_000, 0.07), "non_compliance": (15_000_000, 0.03), "misleading_information": (7_500_000, 0.01)}
GDPR = {"lower_tier": (10_000_000, 0.02), "upper_tier": (20_000_000, 0.04)}

def penalty_calculator(law: str, violation_type: str, annual_turnover_eur: float | None = None):
    law_norm = law.lower(); rules = GDPR if "gdpr" in law_norm else AI_ACT; canonical = "GDPR" if "gdpr" in law_norm else "AI Act"
    vt = violation_type.lower()
    if vt not in rules:
        return None, ToolCall(tool_name="penalty_calculator", arguments=locals(), success=False, observation_summary=f"Unsupported violation type: {violation_type}")
    fixed, pct = rules[vt]; turnover_based = annual_turnover_eur * pct if annual_turnover_eur is not None else None
    max_penalty = max(fixed, turnover_based) if turnover_based is not None else fixed
    calc = f"max({fixed:.0f}, {pct:.2%} * {annual_turnover_eur:.2f}) = {max_penalty:.2f}" if annual_turnover_eur is not None else f"turnover not provided; fixed cap used: {fixed:.0f}"
    result = PenaltyCalculation(law=canonical, violation_type=vt, annual_turnover_eur=annual_turnover_eur, fixed_cap_eur=float(fixed), turnover_percent=pct, turnover_based_eur=turnover_based, maximum_penalty_eur=float(max_penalty), calculation=calc, caveat="Numeric cap only; legal basis must be cited from KB.")
    return result, ToolCall(tool_name="penalty_calculator", arguments={"law": canonical, "violation_type": vt, "annual_turnover_eur": annual_turnover_eur}, success=True, observation_summary=calc)

def _add_months(d: date, months: int) -> date:
    mi = d.month - 1 + months; y = d.year + mi//12; m = mi%12 + 1; day = min(d.day, monthrange(y,m)[1]); return date(y,m,day)
DEADLINES = {"entry_into_force": ("AI Act entry into force", "2024-08-01", 0), "prohibited_practices": ("AI Act prohibited practices rules", "2024-08-01", 6), "gpai_obligations": ("AI Act GPAI obligations", "2024-08-01", 12), "general_application": ("AI Act general application", "2024-08-01", 24), "high_risk_obligations": ("AI Act selected high-risk obligations", "2024-08-01", 36)}

def deadline_calculator(event: str, start_date: str | None = None, months_after_start: int | None = None, reference_date: str | None = None):
    if event in DEADLINES: label, start_date, months_after_start = DEADLINES[event]
    elif not start_date or months_after_start is None: return None, ToolCall(tool_name="deadline_calculator", arguments=locals(), success=False, observation_summary="Custom deadline requires start_date and months_after_start")
    else: label = event
    start = datetime.strptime(str(start_date), "%Y-%m-%d").date(); ref = datetime.strptime(reference_date, "%Y-%m-%d").date() if reference_date else date.today(); deadline = _add_months(start, int(months_after_start)); days=(deadline-ref).days; status="future" if days>0 else "today" if days==0 else "past"
    result = DeadlineCalculation(event=label, start_date=start.isoformat(), months_after_start=int(months_after_start), deadline_date=deadline.isoformat(), reference_date=ref.isoformat(), days_remaining=days, status=status, caveat="Calendar calculation only; legal basis must be cited from KB.")
    return result, ToolCall(tool_name="deadline_calculator", arguments={"event": event, "start_date": start.isoformat(), "months_after_start": int(months_after_start), "reference_date": ref.isoformat()}, success=True, observation_summary=f"{label}: {deadline.isoformat()}, status={status}")

def external_lookup(query: str, timeout: int = 8):
    title = re.sub(r"\s+", " ", query.strip()); url = "https://en.wikipedia.org/api/rest_v1/page/summary/" + urllib.parse.quote(title.replace(" ", "_"))
    try:
        with urllib.request.urlopen(url, timeout=timeout) as resp: payload = json.loads(resp.read().decode("utf-8"))
        result = {"title": payload.get("title"), "extract": payload.get("extract"), "url": payload.get("content_urls",{}).get("desktop",{}).get("page")}
        return result, ToolCall(tool_name="external_lookup", arguments={"query": query}, success=True, observation_summary=(result.get("extract") or "")[:250])
    except Exception as e:
        return {}, ToolCall(tool_name="external_lookup", arguments={"query": query}, success=False, observation_summary=f"{type(e).__name__}: {e}")