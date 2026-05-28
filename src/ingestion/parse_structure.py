"""
Input:  data/processed/documents.jsonl  (one extracted document per line)
Output: data/processed/sections.jsonl   (one logical section per line)

Goal:
    Convert raw document-level text into logical sections before chunking.
    This prevents the chunker from mixing unrelated legal units, e.g. Article 5
    and Article 6, or Annex III and Annex IV.

Supported strategies:
    1. EU/legal texts: Recitals, Articles, Annexes.
    2. Markdown: # / ## / ### heading hierarchy.
    3. Reports/PDFs: numbered headings and uppercase headings.
    4. Fallback: whole document as one section.

Run:
    python src/ingestion/parse_structure.py \
      --in data/processed/documents.jsonl \
      --out data/processed/sections.jsonl \
      --stats data/processed/structure_stats.json \
      --verbose
"""

from __future__ import annotations

import argparse
import bisect
import json
import logging
import re
import sys
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Iterable

log = logging.getLogger("parse_structure")


# ---------------------------------------------------------------------------
# Output schema
# ---------------------------------------------------------------------------

@dataclass
class Section:
    section_id: str
    doc_id: str
    doc_title: str
    doc_url: str
    doc_format: str
    doc_tier: str
    doc_role: str

    section_type: str
    section_number: str | None
    section_title: str
    section_path: list[str]

    text: str
    char_start: int
    char_end: int
    page_start: int | None = None
    page_end: int | None = None

    token_estimate: int = 0
    char_count: int = 0
    warnings: list[str] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

SPACE_RE = re.compile(r"[ \t]+")
NEWLINE_RE = re.compile(r"\n{3,}")


def clean_title(s: str) -> str:
    s = s.replace("`", "")
    s = s.replace("\n", " ")
    s = SPACE_RE.sub(" ", s)
    s = s.strip(" -–—:;.\t\n")
    return s[:180].strip()


def normalize_text(s: str) -> str:
    s = s.replace("\xa0", " ").replace("\u202f", " ")
    s = SPACE_RE.sub(" ", s)
    s = NEWLINE_RE.sub("\n\n", s)
    return s.strip()


def safe_slug(s: str, max_len: int = 70) -> str:
    s = s.lower().strip()
    s = re.sub(r"[^a-z0-9]+", "_", s)
    s = re.sub(r"_+", "_", s).strip("_")
    return s[:max_len] or "section"


def estimate_tokens(text: str) -> int:
    # Good enough for section stats. Stage 3 chunker can use the real tokenizer.
    return int(len(text.split()) * 1.3)


def page_for_offset(page_breaks: list[int], offset: int) -> int | None:
    if not page_breaks:
        return None
    # page_breaks are zero-based char offsets, output page numbers are 1-based.
    return max(1, bisect.bisect_right(page_breaks, offset))


def base_meta(doc: dict[str, Any]) -> dict[str, str]:
    return {
        "doc_id": doc.get("doc_id", ""),
        "doc_title": doc.get("title", ""),
        "doc_url": doc.get("url", ""),
        "doc_format": doc.get("ext") or doc.get("format", ""),
        "doc_tier": doc.get("tier", ""),
        "doc_role": doc.get("role", ""),
    }


def make_section(
    doc: dict[str, Any],
    section_type: str,
    section_number: str | None,
    section_title: str,
    section_path: list[str],
    text: str,
    start: int,
    end: int,
    warnings: list[str] | None = None,
) -> Section:
    text = normalize_text(text)
    page_breaks = doc.get("page_breaks") or []
    page_start = page_for_offset(page_breaks, start)
    page_end = page_for_offset(page_breaks, max(start, end - 1))

    num_slug = safe_slug(section_number or section_title)
    sec_id = f"{doc['doc_id']}__{safe_slug(section_type)}__{num_slug}"

    return Section(
        **base_meta(doc),
        section_id=sec_id,
        section_type=section_type,
        section_number=section_number,
        section_title=clean_title(section_title),
        section_path=[clean_title(x) for x in section_path if clean_title(x)],
        text=text,
        char_start=start,
        char_end=end,
        page_start=page_start,
        page_end=page_end,
        token_estimate=estimate_tokens(text),
        char_count=len(text),
        warnings=warnings or [],
    )


# ---------------------------------------------------------------------------
# Legal parser: Articles / Annexes / Recitals
# ---------------------------------------------------------------------------

# Matches true Article headings in flattened EUR-Lex HTML/PDF text.
# It intentionally excludes cross-references like "Article 5 of Regulation...".
ARTICLE_HEADING_RE = re.compile(
    r"\bArticle\s+(\d+[A-Z]?)\s+"
    r"(?!of\b|thereof\b|TFEU\b|TEU\b|point\b|points\b|and\b|to\b|[0-9(])"
    r"([A-Z][A-Za-z0-9’'‘“”\"`,(),/\-–—:; &\.\n]{2,180}?)"
    r"(?=\s+(?:"
    r"1\.|For the purposes|This Regulation|This Directive|The purpose|Providers|Deployers|"
    r"Importers|Distributors|Member States|Each Member State|The Commission|Natural|Legal|"
    r"High-risk|AI systems|No |It |Where|By way|Before|Without prejudice|Any |A |An |"
    r"Chapter|CHAPTER|Section|SECTION|Article\s+\d+|ANNEX|Annex|The data subject|Processing"
    r"))",
    re.S,
)


ARTICLE_LINE_HEADING_RE = re.compile(
    r"(?m)^Article\s+(\d+[A-Z]?)\s*\n([^\n]{2,180})\s*(?:\n|$)"
)

ANNEX_HEADING_RE = re.compile(
    r"\bANNEX\s+([IVXLCDM]+|\d+[A-Z]?)\s+([A-Z][A-Z0-9 ,;:\-–—/'()\n]{2,220})?",
    re.S,
)


def article_int(num: str) -> int | None:
    m = re.match(r"\d+", num)
    return int(m.group(0)) if m else None


def filter_article_headings(matches: list[re.Match]) -> list[re.Match]:
    """Keep a mostly increasing Article sequence and drop late cross-references."""
    out: list[re.Match] = []
    prev = 0
    for m in matches:
        n = article_int(m.group(1))
        if n is None:
            continue
        # Legal acts should progress mostly 1,2,3...; allow small jumps because
        # some headings are harder to detect in messy HTML/PDF text.
        if n > prev and (prev == 0 or n == prev + 1 or n <= prev + 5):
            out.append(m)
            prev = n
    return out


def parse_recitals(doc: dict[str, Any], first_article_start: int | None) -> list[Section]:
    text = doc["text"]
    end_limit = first_article_start if first_article_start is not None else min(len(text), 200_000)
    preamble = text[:end_limit]

    raw = list(re.finditer(r"(?<![A-Za-z0-9])\((\d{1,3})\)\s+", preamble))
    if not raw:
        return []

    # Find the longest consecutive run beginning at recital (1).
    start_idx = None
    for i, m in enumerate(raw):
        if m.group(1) == "1":
            start_idx = i
            break
    if start_idx is None:
        return []

    selected: list[re.Match] = []
    expected = 1
    for m in raw[start_idx:]:
        n = int(m.group(1))
        if n == expected:
            selected.append(m)
            expected += 1
        elif n > expected + 3:
            # Strong jump means we probably left the recital block.
            break

    if len(selected) < 3:
        return []

    sections: list[Section] = []
    for i, m in enumerate(selected):
        start = m.start()
        end = selected[i + 1].start() if i + 1 < len(selected) else end_limit
        number = m.group(1)
        body = text[start:end]
        sections.append(make_section(
            doc,
            section_type="recital",
            section_number=number,
            section_title=f"Recital {number}",
            section_path=[f"Recital {number}"],
            text=body,
            start=start,
            end=end,
        ))
    return sections


def parse_annexes(doc: dict[str, Any], start_after: int = 0) -> list[Section]:
    text = doc["text"]
    raw = [m for m in ANNEX_HEADING_RE.finditer(text) if m.start() >= start_after]
    if not raw:
        return []

    sections: list[Section] = []
    for i, m in enumerate(raw):
        start = m.start()
        end = raw[i + 1].start() if i + 1 < len(raw) else len(text)
        num = clean_title(m.group(1))
        title = clean_title(m.group(2) or f"Annex {num}")
        # Drop obvious false positives that are too tiny.
        if end - start < 200:
            continue
        sections.append(make_section(
            doc,
            section_type="annex",
            section_number=num,
            section_title=title,
            section_path=[f"Annex {num}", title],
            text=text[start:end],
            start=start,
            end=end,
        ))
    return sections


def parse_legal_articles(doc: dict[str, Any]) -> list[Section]:
    text = doc["text"]
    raw = list(ARTICLE_HEADING_RE.finditer(text)) + list(ARTICLE_LINE_HEADING_RE.finditer(text))
    raw = sorted(raw, key=lambda m: m.start())
    # Deduplicate when both regexes catch the same heading.
    deduped = []
    seen_starts = set()
    for m in raw:
        bucket = m.start() // 5
        if bucket in seen_starts:
            continue
        seen_starts.add(bucket)
        deduped.append(m)
    articles = filter_article_headings(deduped)
    if len(articles) < 5:
        return []

    sections: list[Section] = []
    annexes = parse_annexes(doc, start_after=articles[-1].end())
    annex_start = min((a.char_start for a in annexes), default=len(text))

    for i, m in enumerate(articles):
        start = m.start()
        next_start = articles[i + 1].start() if i + 1 < len(articles) else annex_start
        if next_start <= start:
            continue

        num = m.group(1)
        title = clean_title(m.group(2))
        sections.append(make_section(
            doc,
            section_type="article",
            section_number=num,
            section_title=title,
            section_path=[f"Article {num}", title],
            text=text[start:next_start],
            start=start,
            end=next_start,
        ))

    # Optional recital sections before Article 1.
    recitals = parse_recitals(doc, first_article_start=articles[0].start())
    return recitals + sections + annexes


# ---------------------------------------------------------------------------
# Markdown parser
# ---------------------------------------------------------------------------

MD_HEADING_RE = re.compile(r"^(#{1,6})\s+(.+?)\s*$", re.M)


def parse_markdown(doc: dict[str, Any]) -> list[Section]:
    text = doc["text"]
    matches = list(MD_HEADING_RE.finditer(text))
    if not matches:
        return []

    stack: list[tuple[int, str]] = []
    sections: list[Section] = []

    for i, m in enumerate(matches):
        level = len(m.group(1))
        title = clean_title(m.group(2))
        start = m.start()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(text)

        stack = [(lvl, t) for lvl, t in stack if lvl < level]
        stack.append((level, title))
        path = [t for _, t in stack]

        # Skip empty heading-only sections.
        if len(text[start:end].strip()) < 80:
            continue

        sections.append(make_section(
            doc,
            section_type=f"h{level}",
            section_number=None,
            section_title=title,
            section_path=path,
            text=text[start:end],
            start=start,
            end=end,
        ))
    return sections


# ---------------------------------------------------------------------------
# Generic report/PDF parser
# ---------------------------------------------------------------------------

REPORT_HEADING_RE = re.compile(
    r"^\s*((?:\d{1,2})(?:\.\d{1,2}){0,3})[.)]?\s+([A-Z][^\n]{4,140})\s*$|"
    r"^\s*([A-Z][A-Z0-9 ,;:\-–—/'()]{8,120})\s*$",
    re.M,
)

BAD_REPORT_HEADINGS = {
    "table of contents", "contents", "references", "acknowledgements", "abstract"
}


def parse_report_headings(doc: dict[str, Any]) -> list[Section]:
    text = doc["text"]
    raw = []
    for m in REPORT_HEADING_RE.finditer(text):
        number = m.group(1)
        title = clean_title(m.group(2) or m.group(3) or "")
        if not title or title.lower() in BAD_REPORT_HEADINGS:
            continue
        if len(title.split()) > 18:
            continue
        raw.append((m.start(), number, title))

    # Too many headings usually means table rows/noisy PDF extraction.
    if len(raw) < 3 or len(raw) > 120:
        return []

    sections: list[Section] = []
    for i, (start, number, title) in enumerate(raw):
        end = raw[i + 1][0] if i + 1 < len(raw) else len(text)
        if end - start < 300:
            continue
        section_type = "numbered_heading" if number else "heading"
        sec_number = number
        path_title = f"{number} {title}" if number else title
        sections.append(make_section(
            doc,
            section_type=section_type,
            section_number=sec_number,
            section_title=title,
            section_path=[path_title],
            text=text[start:end],
            start=start,
            end=end,
        ))
    return sections


# ---------------------------------------------------------------------------
# Router and main
# ---------------------------------------------------------------------------

LEGAL_DOC_HINTS = (
    "ai_act_2024_1689",
    "gdpr_2016_679",
    "dsa_2022_2065",
    "pld_2024_2853",
    "ai_act_proposal_2021",
    "ai_act_trilogue_dec2023",
    "coe_ai_convention_2024",
)


def fallback_section(doc: dict[str, Any], reason: str) -> list[Section]:
    text = doc.get("text", "")
    return [make_section(
        doc,
        section_type="document",
        section_number=None,
        section_title=doc.get("title") or doc.get("doc_id", "document"),
        section_path=[doc.get("title") or doc.get("doc_id", "document")],
        text=text,
        start=0,
        end=len(text),
        warnings=[f"fallback:{reason}"],
    )]


def parse_doc(doc: dict[str, Any]) -> list[Section]:
    doc_id = doc.get("doc_id", "")
    fmt = (doc.get("ext") or doc.get("format") or "").lower()

    # 1) Legal docs: strong article/annex parser.
    if any(h in doc_id for h in LEGAL_DOC_HINTS) or "Regulation (EU)" in doc.get("title", ""):
        sections = parse_legal_articles(doc)
        if sections:
            return sections

    # 2) Markdown: native heading parser.
    if fmt == "md":
        sections = parse_markdown(doc)
        if sections:
            return sections

    # 3) Any document can still contain article headings.
    sections = parse_legal_articles(doc)
    if len([s for s in sections if s.section_type == "article"]) >= 5:
        return sections

    # 4) Reports/PDFs: generic heading parser.
    sections = parse_report_headings(doc)
    if sections:
        return sections

    # 5) Fallback.
    return fallback_section(doc, "no_structure_detected")


def load_jsonl(path: Path) -> Iterable[dict[str, Any]]:
    with path.open("r", encoding="utf-8") as f:
        for line_no, line in enumerate(f, start=1):
            line = line.strip()
            if not line:
                continue
            try:
                yield json.loads(line)
            except json.JSONDecodeError as e:
                raise ValueError(f"Invalid JSON on line {line_no} in {path}: {e}") from e


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--in", dest="input", default="data/processed/documents.jsonl")
    ap.add_argument("--out", default="data/processed/sections.jsonl")
    ap.add_argument("--stats", default="data/processed/structure_stats.json")
    ap.add_argument("--min-section-chars", type=int, default=120)
    ap.add_argument("--verbose", action="store_true")
    args = ap.parse_args()

    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(asctime)s | %(levelname)-7s | %(message)s",
        datefmt="%H:%M:%S",
    )

    input_path = Path(args.input)
    out_path = Path(args.out)
    stats_path = Path(args.stats)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    stats_path.parent.mkdir(parents=True, exist_ok=True)

    docs = list(load_jsonl(input_path))
    log.info("starting structure parsing: docs=%d input=%s", len(docs), input_path)

    all_sections: list[Section] = []
    per_doc = []

    for doc in docs:
        doc_id = doc.get("doc_id", "")
        sections = parse_doc(doc)
        sections = [s for s in sections if s.char_count >= args.min_section_chars]
        all_sections.extend(sections)

        by_type: dict[str, int] = {}
        warnings: list[str] = []
        for s in sections:
            by_type[s.section_type] = by_type.get(s.section_type, 0) + 1
            warnings.extend(s.warnings)

        article_nums = [int(s.section_number) for s in sections
                        if s.section_type == "article" and s.section_number and s.section_number.isdigit()]
        missing_articles = []
        if article_nums and max(article_nums) <= 200:
            got = set(article_nums)
            missing_articles = [n for n in range(1, max(article_nums) + 1) if n not in got]

        log.info("[ok] %-45s sections=%-4d types=%s%s",
                 doc_id, len(sections), by_type,
                 f" missing_articles={missing_articles[:20]}" if missing_articles else "")

        per_doc.append({
            "doc_id": doc_id,
            "title": doc.get("title", ""),
            "format": doc.get("ext") or doc.get("format", ""),
            "sections": len(sections),
            "by_type": by_type,
            "missing_articles": missing_articles,
            "warnings": sorted(set(warnings)),
        })

    with out_path.open("w", encoding="utf-8") as f:
        for s in all_sections:
            f.write(json.dumps(asdict(s), ensure_ascii=False) + "\n")

    stats = {
        "input_documents": len(docs),
        "total_sections": len(all_sections),
        "by_section_type": {},
        "documents": per_doc,
    }
    for s in all_sections:
        stats["by_section_type"][s.section_type] = stats["by_section_type"].get(s.section_type, 0) + 1

    stats_path.write_text(json.dumps(stats, indent=2, ensure_ascii=False), encoding="utf-8")
    log.info("wrote sections: %s", out_path)
    log.info("wrote stats: %s", stats_path)
    log.info("SUMMARY sections=%d by_type=%s", len(all_sections), stats["by_section_type"])
    return 0


if __name__ == "__main__":
    sys.exit(main())
