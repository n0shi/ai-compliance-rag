"""
Reads logical sections from sections.jsonl and produces retrieval-ready chunks.
This stage intentionally chunks *inside* sections rather than across document
boundaries, so legal units such as Article 5, Article 50, Annex III, GDPR
Article 22, etc. are not accidentally merged with neighbouring sections.

Input:
    data/processed/sections.jsonl
Optional input:
    data/processed/documents.jsonl   # used to map PDF char offsets to pages

Output:
    data/processed/chunks.jsonl
    data/processed/chunk_stats.json

Example:
    python src/ingestion/chunker.py \
      --sections data/processed/sections.jsonl \
      --documents data/processed/documents.jsonl \
      --out data/processed/chunks_800_120.jsonl \
      --stats data/processed/chunk_stats_800_120.json \
      --chunk-size 800 \
      --overlap 120 \
      --verbose

Why section-aware chunking?
    RAG over legal/compliance documents is harmed when chunks cross semantic
    boundaries, e.g. the end of Article 5 and the beginning of Article 6. This
    chunker first respects sections produced by parse_structure.py, then applies
    token-budget chunking with overlap within each section.
"""

from __future__ import annotations

import argparse
import bisect
import json
import logging
import re
import sys
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable, Optional

log = logging.getLogger("chunker")


# ---------------------------------------------------------------------------
# Token counting
# ---------------------------------------------------------------------------

_TOKENIZER: Any = None


def count_tokens(text: str) -> int:
    """Count tokens with cl100k_base when available, else word-count estimate.

    The pipeline uses this counter consistently for chunk-size experiments. For
    a production model, replace this with the exact embedding/reranker tokenizer.
    """
    global _TOKENIZER
    if not text:
        return 0
    if _TOKENIZER == "FALLBACK":
        return max(1, int(len(text.split()) * 1.3)) if text.split() else 0
    if _TOKENIZER is None:
        try:
            import tiktoken
            _TOKENIZER = tiktoken.get_encoding("cl100k_base")
        except Exception as e:
            log.warning("tiktoken unavailable (%s); using word-count×1.3 estimate", type(e).__name__)
            _TOKENIZER = "FALLBACK"
            return max(1, int(len(text.split()) * 1.3)) if text.split() else 0
    return len(_TOKENIZER.encode(text, disallowed_special=()))


# ---------------------------------------------------------------------------
# Schema
# ---------------------------------------------------------------------------


@dataclass
class Chunk:
    chunk_id: str
    section_id: str

    doc_id: str
    doc_title: str
    doc_url: str
    doc_format: str
    doc_tier: str
    doc_role: str

    section_type: str
    section_number: Optional[str]
    section_title: str
    section_path: list[str]

    chunk_index: int
    chunks_in_section: int

    char_start: int
    char_end: int
    page_start: Optional[int]
    page_end: Optional[int]

    token_count: int
    char_count: int
    text: str

    embedding_text: str
    bm25_text: str
    context_before: str = ""
    context_after: str = ""

    is_distractor: bool = False
    is_duplicate: bool = False
    is_poisoned: bool = False

    warnings: list[str] = field(default_factory=list)


@dataclass
class TextUnit:
    text: str
    start: int  # local char offset inside section text
    end: int
    tokens: int


# ---------------------------------------------------------------------------
# Text splitting helpers
# ---------------------------------------------------------------------------


_WS_RE = re.compile(r"[ \t]+")
_SENTENCE_BOUNDARY_RE = re.compile(
    r"(?<=[.!?])\s+(?=(?:[A-Z0-9(\[]|Article\s+\d+|Annex\s+[IVXLC]+))"
)


def normalize_chunk_text(text: str) -> str:
    text = text.replace("\xa0", " ").replace("\u202f", " ")
    text = _WS_RE.sub(" ", text)
    text = re.sub(r"\n{4,}", "\n\n\n", text)
    return text.strip()


def is_toc_like(text: str) -> bool:
    """Detect table-of-contents / index chunks from PDFs.

    These lines often look relevant to BM25 (many headings + page numbers),
    but they do not contain answer evidence, so we skip them before indexing.
    """
    lines = [ln.strip() for ln in (text or "").splitlines() if ln.strip()]
    if len(lines) < 5:
        return False

    dot_leader = sum(1 for ln in lines if "....." in ln)
    page_refs = sum(1 for ln in lines if re.search(r"\.{3,}\s*\d+\s*$", ln))
    numbered_toc = sum(1 for ln in lines if re.search(r"^\d+(?:\.\d+)*\.?\s+.+\s+\d+\s*$", ln))

    return (dot_leader / len(lines) > 0.25
            or page_refs / len(lines) > 0.25
            or numbered_toc / len(lines) > 0.45)


def iter_paragraph_spans(text: str) -> list[tuple[str, int, int]]:
    """Return paragraph-like spans.

    First tries blank-line paragraphs. If a section is one huge flow-text block
    (common for HTML extracted from EUR-Lex), returns one paragraph and the next
    stage will split it into sentence units.
    """
    spans: list[tuple[str, int, int]] = []
    for m in re.finditer(r"\S(?:.*?\S)?(?=\n\s*\n|\Z)", text, flags=re.DOTALL):
        raw = m.group(0)
        clean = normalize_chunk_text(raw)
        if clean:
            # Find trimmed boundaries inside the raw match.
            leading = len(raw) - len(raw.lstrip())
            trailing = len(raw.rstrip())
            start = m.start() + leading
            end = m.start() + trailing
            spans.append((clean, start, end))
    return spans


def split_long_unit_to_sentences(text: str, start_offset: int, max_tokens: int) -> list[TextUnit]:
    """Split a long paragraph into sentence-ish units; hard split if needed."""
    pieces: list[tuple[str, int, int]] = []
    cursor = 0
    for m in _SENTENCE_BOUNDARY_RE.finditer(text):
        end = m.start()
        part = text[cursor:end].strip()
        if part:
            # Map stripped part back approximately.
            local_start = cursor + (len(text[cursor:end]) - len(text[cursor:end].lstrip()))
            local_end = end - (len(text[cursor:end]) - len(text[cursor:end].rstrip()))
            pieces.append((part, start_offset + local_start, start_offset + local_end))
        cursor = m.end()
    tail = text[cursor:].strip()
    if tail:
        local_start = cursor + (len(text[cursor:]) - len(text[cursor:].lstrip()))
        local_end = len(text) - (len(text[cursor:]) - len(text[cursor:].rstrip()))
        pieces.append((tail, start_offset + local_start, start_offset + local_end))

    # If sentence detection failed, use the whole unit.
    if not pieces:
        pieces = [(text, start_offset, start_offset + len(text))]

    units: list[TextUnit] = []
    for piece, s, e in pieces:
        n = count_tokens(piece)
        if n <= max_tokens:
            units.append(TextUnit(piece, s, e, n))
        else:
            units.extend(hard_split_by_words(piece, s, max_tokens=max_tokens))
    return units


def hard_split_by_words(text: str, start_offset: int, max_tokens: int) -> list[TextUnit]:
    """Last-resort splitter for very long sentences/tables."""
    # max words approximate; leave margin because tokens >= words.
    max_words = max(80, int(max_tokens / 1.3))
    words = list(re.finditer(r"\S+", text))
    if not words:
        return []
    units: list[TextUnit] = []
    for i in range(0, len(words), max_words):
        group = words[i:i + max_words]
        s_local = group[0].start()
        e_local = group[-1].end()
        piece = text[s_local:e_local].strip()
        units.append(TextUnit(piece, start_offset + s_local, start_offset + e_local, count_tokens(piece)))
    return units


def make_text_units(section_text: str, max_unit_tokens: int) -> list[TextUnit]:
    """Create units that are smaller than the chunk budget.

    Units are paragraphs where possible, sentences when paragraphs are too long,
    and word windows as a last resort.
    """
    text = section_text or ""
    paragraphs = iter_paragraph_spans(text)
    if not paragraphs:
        return []

    units: list[TextUnit] = []
    for para, start, end in paragraphs:
        n = count_tokens(para)
        if n <= max_unit_tokens:
            units.append(TextUnit(para, start, end, n))
        else:
            units.extend(split_long_unit_to_sentences(para, start, max_tokens=max_unit_tokens))
    return units


# ---------------------------------------------------------------------------
# Chunk construction
# ---------------------------------------------------------------------------


def build_chunks_from_units(units: list[TextUnit], chunk_size: int, overlap: int, min_chunk_tokens: int = 80) -> list[list[TextUnit]]:
    """Greedy chunking with unit-level overlap.

    Uses semantic units instead of fixed token slices. The overlap is implemented
    by carrying the last N tokens worth of units into the next chunk.
    """
    if not units:
        return []

    chunks: list[list[TextUnit]] = []
    current: list[TextUnit] = []
    current_tokens = 0

    def flush_current() -> list[TextUnit]:
        nonlocal current, current_tokens
        out = current[:]
        # Build overlap tail.
        tail: list[TextUnit] = []
        tail_tokens = 0
        for u in reversed(current):
            if tail_tokens >= overlap:
                break
            tail.insert(0, u)
            tail_tokens += u.tokens
        current = tail
        current_tokens = tail_tokens
        return out

    for u in units:
        # If adding this unit exceeds budget and current has non-overlap content, flush.
        if current and current_tokens + u.tokens > chunk_size and current_tokens >= min_chunk_tokens:
            out = flush_current()
            if out:
                chunks.append(out)

            # Avoid infinite duplicate chunks when one overlap tail plus unit still exceeds.
            if current and current_tokens + u.tokens > chunk_size:
                current = []
                current_tokens = 0

        current.append(u)
        current_tokens += u.tokens

    if current:
        # Do not append a final chunk that is exactly a duplicate of the previous overlap tail.
        if not chunks or [u.start for u in chunks[-1]] != [u.start for u in current]:
            chunks.append(current)

    return chunks


def safe_slug(value: Any, max_len: int = 80) -> str:
    s = "" if value is None else str(value)
    s = re.sub(r"[^a-zA-Z0-9]+", "_", s).strip("_").lower()
    return s[:max_len] or "section"


def build_chunk_id(section: dict[str, Any], idx: int) -> str:
    return f"{section['section_id']}__chunk_{idx + 1:03d}"


def build_retrieval_texts(section: dict[str, Any], chunk_text: str) -> tuple[str, str]:
    title = section.get("doc_title") or section.get("doc_id") or ""
    path = " > ".join(section.get("section_path") or [])
    section_title = section.get("section_title") or ""
    header_parts = [title]
    if path:
        header_parts.append(path)
    elif section_title:
        header_parts.append(section_title)
    header = "\n".join(p for p in header_parts if p)

    embedding_text = normalize_chunk_text(f"{header}\n{chunk_text}")

    # BM25 benefits from repeated compact metadata terms: article number, title,
    # role and title. Keep legal words like shall/not/except in the original text.
    bm25_prefix = " ".join(str(x) for x in [
        section.get("doc_title", ""),
        section.get("section_type", ""),
        section.get("section_number", ""),
        section.get("section_title", ""),
        " ".join(section.get("section_path") or []),
    ] if x)
    bm25_text = normalize_chunk_text(f"{bm25_prefix} {chunk_text}")
    return embedding_text, bm25_text


def short_context(text: str, start: int, end: int, window: int = 320) -> tuple[str, str]:
    before = normalize_chunk_text(text[max(0, start - window):start])
    after = normalize_chunk_text(text[end:min(len(text), end + window)])
    return before[-window:], after[:window]


def load_documents_pages(path: Optional[Path]) -> dict[str, list[int]]:
    if not path or not path.exists():
        return {}
    pages: dict[str, list[int]] = {}
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            if not line.strip():
                continue
            d = json.loads(line)
            pb = d.get("page_breaks") or []
            if pb:
                pages[d["doc_id"]] = pb
    return pages


def page_for_offset(page_breaks: list[int], char_offset: int) -> Optional[int]:
    if not page_breaks:
        return None
    # page_breaks are 0-based offsets, page number is index + 1.
    idx = bisect.bisect_right(page_breaks, max(0, char_offset)) - 1
    return max(1, idx + 1)


def pages_for_chunk(section: dict[str, Any], local_start: int, local_end: int, doc_pages: dict[str, list[int]]) -> tuple[Optional[int], Optional[int]]:
    doc_id = section.get("doc_id")
    page_breaks = doc_pages.get(doc_id, [])
    if page_breaks:
        global_start = int(section.get("char_start") or 0) + local_start
        global_end = int(section.get("char_start") or 0) + max(local_start, local_end - 1)
        return page_for_offset(page_breaks, global_start), page_for_offset(page_breaks, global_end)
    return section.get("page_start"), section.get("page_end")


def role_flags(role: str) -> tuple[bool, bool, bool]:
    role_l = (role or "").lower()
    return role_l == "distractor", role_l == "duplicate", role_l == "poisoned"


def chunk_section(section: dict[str, Any], chunk_size: int, overlap: int, doc_pages: dict[str, list[int]]) -> list[Chunk]:
    text = section.get("text") or ""
    text = normalize_chunk_text(text)
    warnings = list(section.get("warnings") or [])

    if not text:
        return []

    units = make_text_units(text, max_unit_tokens=max(128, chunk_size))
    grouped = build_chunks_from_units(units, chunk_size=chunk_size, overlap=overlap, min_chunk_tokens=80)

    out: list[Chunk] = []
    chunks_in_section = len(grouped)
    is_distractor, is_duplicate, is_poisoned = role_flags(section.get("doc_role", ""))

    for idx, group in enumerate(grouped):
        local_start = min(u.start for u in group)
        local_end = max(u.end for u in group)
        chunk_text = normalize_chunk_text("\n\n".join(u.text for u in group))
        token_count = count_tokens(chunk_text)
        page_start, page_end = pages_for_chunk(section, local_start, local_end, doc_pages)
        context_before, context_after = short_context(text, local_start, local_end)
        embedding_text, bm25_text = build_retrieval_texts(section, chunk_text)

        chunk_warnings = warnings[:]
        if token_count > int(chunk_size * 1.35):
            chunk_warnings.append(f"oversized_chunk:{token_count}")
        if token_count < 40:
            chunk_warnings.append("very_short_chunk")

        out.append(Chunk(
            chunk_id=build_chunk_id(section, idx),
            section_id=section["section_id"],
            doc_id=section.get("doc_id", ""),
            doc_title=section.get("doc_title", ""),
            doc_url=section.get("doc_url", ""),
            doc_format=section.get("doc_format", ""),
            doc_tier=section.get("doc_tier", ""),
            doc_role=section.get("doc_role", ""),
            section_type=section.get("section_type", ""),
            section_number=section.get("section_number"),
            section_title=section.get("section_title", ""),
            section_path=section.get("section_path") or [],
            chunk_index=idx,
            chunks_in_section=chunks_in_section,
            char_start=int(section.get("char_start") or 0) + local_start,
            char_end=int(section.get("char_start") or 0) + local_end,
            page_start=page_start,
            page_end=page_end,
            token_count=token_count,
            char_count=len(chunk_text),
            text=chunk_text,
            embedding_text=embedding_text,
            bm25_text=bm25_text,
            context_before=context_before,
            context_after=context_after,
            is_distractor=is_distractor,
            is_duplicate=is_duplicate,
            is_poisoned=is_poisoned,
            warnings=chunk_warnings,
        ))
    return out


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def setup_logging(verbose: bool = False) -> None:
    logging.basicConfig(
        format="%(asctime)s | %(levelname)-7s | %(message)s",
        datefmt="%H:%M:%S",
        level=logging.DEBUG if verbose else logging.INFO,
    )


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--sections", default="data/processed/sections.jsonl")
    ap.add_argument("--documents", default="data/processed/documents.jsonl", help="Optional; used for PDF page mapping")
    ap.add_argument("--out", default="data/processed/chunks.jsonl")
    ap.add_argument("--stats", default="data/processed/chunk_stats.json")
    ap.add_argument("--chunk-size", type=int, default=800)
    ap.add_argument("--overlap", type=int, default=120)
    ap.add_argument("--min-section-tokens", type=int, default=0, help="Skip tiny sections below this token count; default keeps all")
    ap.add_argument("--keep-toc", action="store_true", help="Keep table-of-contents-like sections; default skips them")
    ap.add_argument("--verbose", action="store_true")
    args = ap.parse_args()

    setup_logging(args.verbose)

    sections_path = Path(args.sections)
    documents_path = Path(args.documents) if args.documents else None
    out_path = Path(args.out)
    stats_path = Path(args.stats)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    stats_path.parent.mkdir(parents=True, exist_ok=True)

    if args.overlap >= args.chunk_size:
        log.error("overlap must be smaller than chunk-size")
        return 1
    if not sections_path.exists():
        log.error("sections file not found: %s", sections_path)
        return 1

    doc_pages = load_documents_pages(documents_path)
    log.info("loaded page maps for %d PDF documents", len(doc_pages))

    chunks: list[Chunk] = []
    sections_seen = 0
    skipped = 0
    skipped_toc_like = 0
    by_doc: dict[str, int] = {}
    by_format: dict[str, int] = {}
    by_role: dict[str, int] = {}
    by_section_type: dict[str, int] = {}

    log.info("chunking sections=%s chunk_size=%d overlap=%d", sections_path, args.chunk_size, args.overlap)
    with sections_path.open("r", encoding="utf-8") as f:
        for line in f:
            if not line.strip():
                continue
            sec = json.loads(line)
            sections_seen += 1
            if args.min_section_tokens and int(sec.get("token_estimate") or 0) < args.min_section_tokens:
                skipped += 1
                continue
            if not args.keep_toc and is_toc_like(sec.get("text") or ""):
                skipped_toc_like += 1
                skipped += 1
                continue
            cs = chunk_section(sec, args.chunk_size, args.overlap, doc_pages)
            chunks.extend(cs)
            if args.verbose and sections_seen % 250 == 0:
                log.debug("processed sections=%d chunks=%d", sections_seen, len(chunks))

    with out_path.open("w", encoding="utf-8") as f:
        for c in chunks:
            f.write(json.dumps(asdict(c), ensure_ascii=False) + "\n")
            by_doc[c.doc_id] = by_doc.get(c.doc_id, 0) + 1
            by_format[c.doc_format] = by_format.get(c.doc_format, 0) + 1
            by_role[c.doc_role] = by_role.get(c.doc_role, 0) + 1
            by_section_type[c.section_type] = by_section_type.get(c.section_type, 0) + 1

    token_counts = [c.token_count for c in chunks]
    token_counts_sorted = sorted(token_counts)

    def pct(p: float) -> int:
        if not token_counts_sorted:
            return 0
        idx = min(len(token_counts_sorted) - 1, int(round((len(token_counts_sorted) - 1) * p)))
        return token_counts_sorted[idx]

    stats = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "source_sections": str(sections_path),
        "chunk_size": args.chunk_size,
        "overlap": args.overlap,
        "sections_seen": sections_seen,
        "sections_skipped": skipped,
        "toc_like_sections_skipped": skipped_toc_like,
        "chunks": len(chunks),
        "total_tokens": sum(token_counts),
        "avg_tokens_per_chunk": round(sum(token_counts) / len(token_counts), 2) if token_counts else 0,
        "min_tokens": min(token_counts) if token_counts else 0,
        "p25_tokens": pct(0.25),
        "p50_tokens": pct(0.50),
        "p75_tokens": pct(0.75),
        "p90_tokens": pct(0.90),
        "p95_tokens": pct(0.95),
        "max_tokens": max(token_counts) if token_counts else 0,
        "oversized_chunks": sum(1 for c in chunks if any(w.startswith("oversized_chunk") for w in c.warnings)),
        "very_short_chunks": sum(1 for c in chunks if "very_short_chunk" in c.warnings),
        "by_doc": dict(sorted(by_doc.items())),
        "by_format": dict(sorted(by_format.items())),
        "by_role": dict(sorted(by_role.items())),
        "by_section_type": dict(sorted(by_section_type.items())),
    }
    stats_path.write_text(json.dumps(stats, indent=2, ensure_ascii=False), encoding="utf-8")

    log.info("wrote chunks: %s", out_path)
    log.info("wrote stats: %s", stats_path)
    log.info("SUMMARY chunks=%d avg_tokens=%.1f p50=%d p90=%d max=%d oversized=%d very_short=%d skipped_toc=%d",
             stats["chunks"], stats["avg_tokens_per_chunk"], stats["p50_tokens"], stats["p90_tokens"],
             stats["max_tokens"], stats["oversized_chunks"], stats["very_short_chunks"],
             stats["toc_like_sections_skipped"])

    return 0


if __name__ == "__main__":
    sys.exit(main())
