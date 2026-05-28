"""
Input:
    data/raw/corpus_manifest.json + raw PDF/HTML/MD files

Output:
    data/processed/documents.jsonl       # one extracted document per line
    data/processed/ingestion_stats.json  # aggregate stats
    data/processed/extraction_log.jsonl   # detailed per-document extraction log

Extracts and normalizes document text.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import logging
import re
import sys
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from time import perf_counter
from typing import Any, Optional


# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------

def setup_logging(log_file: Optional[Path] = None, verbose: bool = False) -> logging.Logger:
    logger = logging.getLogger("extract")
    logger.setLevel(logging.DEBUG if verbose else logging.INFO)
    logger.handlers.clear()

    fmt = logging.Formatter(
        fmt="%(asctime)s | %(levelname)-7s | %(message)s",
        datefmt="%H:%M:%S",
    )

    console = logging.StreamHandler(sys.stdout)
    console.setLevel(logging.DEBUG if verbose else logging.INFO)
    console.setFormatter(fmt)
    logger.addHandler(console)

    if log_file:
        log_file.parent.mkdir(parents=True, exist_ok=True)
        fh = logging.FileHandler(log_file, encoding="utf-8")
        fh.setLevel(logging.DEBUG)
        fh.setFormatter(fmt)
        logger.addHandler(fh)

    return logger


log = logging.getLogger("extract")


# ---------------------------------------------------------------------------
# Output schema
# ---------------------------------------------------------------------------

@dataclass
class ExtractedDocument:
    doc_id: str
    title: str
    url: str
    source_path: str
    filename: str
    format: str
    doc_type: str = ""
    tier: str = ""
    role: str = ""
    parser: str = ""
    text: str = ""
    char_count: int = 0
    word_count: int = 0
    token_count: int = 0
    page_breaks: list[int] = field(default_factory=list)
    page_count: int = 0
    sha256: str = ""
    bytes: int = 0
    extracted_at: str = ""
    warnings: list[str] = field(default_factory=list)


@dataclass
class ExtractionEvent:
    doc_id: str
    filename: str
    status: str
    parser: str = ""
    format: str = ""
    bytes: int = 0
    chars: int = 0
    words: int = 0
    tokens: int = 0
    pages: int = 0
    elapsed_ms: int = 0
    warnings: list[str] = field(default_factory=list)
    error: str = ""
    sha256_ok: Optional[bool] = None
    extracted_at: str = ""


# ---------------------------------------------------------------------------
# Tokenizer
# ---------------------------------------------------------------------------

_TOKENIZER: Any = None


def count_tokens(text: str) -> int:
    """Count tokens with cl100k_base. Fall back to word_count * 1.3."""
    global _TOKENIZER

    if _TOKENIZER == "FALLBACK":
        return int(len(text.split()) * 1.3)

    if _TOKENIZER is None:
        try:
            import tiktoken
            _TOKENIZER = tiktoken.get_encoding("cl100k_base")
        except Exception as e:
            log.warning("tiktoken unavailable (%s); using word_count*1.3 estimate", type(e).__name__)
            _TOKENIZER = "FALLBACK"
            return int(len(text.split()) * 1.3)

    return len(_TOKENIZER.encode(text, disallowed_special=()))


# ---------------------------------------------------------------------------
# Cleaning helpers
# ---------------------------------------------------------------------------

def normalize_text(text: str, preserve_newlines: bool = True) -> str:
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = text.replace("\xa0", " ").replace("\u202f", " ")
    text = re.sub(r"[ \t]+", " ", text)

    if preserve_newlines:
        text = re.sub(r" *\n *", "\n", text)
        text = re.sub(r"\n{3,}", "\n\n", text)
    else:
        text = re.sub(r"\s+", " ", text)

    return text.strip()


def sha256_of_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def detect_encoding(raw: bytes) -> tuple[str, str, list[str]]:
    warnings: list[str] = []
    for enc in ("utf-8", "cp1252", "latin-1"):
        try:
            return raw.decode(enc), enc, warnings
        except UnicodeDecodeError:
            continue
    warnings.append("encoding_fallback_replace")
    return raw.decode("utf-8", errors="replace"), "utf-8-replace", warnings


# ---------------------------------------------------------------------------
# PDF parser
# ---------------------------------------------------------------------------

def _remove_running_headers_footers(pages: list[str], min_repeat_ratio: float = 0.5) -> tuple[list[str], int]:
    if len(pages) < 4:
        return pages, 0

    candidates: dict[str, int] = {}
    for page in pages:
        lines = [ln.strip() for ln in page.splitlines() if ln.strip()]
        for ln in lines[:2] + lines[-2:]:
            if 8 <= len(ln) <= 120:
                candidates[ln] = candidates.get(ln, 0) + 1

    threshold = max(3, int(len(pages) * min_repeat_ratio))
    to_remove = {ln for ln, count in candidates.items() if count >= threshold}

    if not to_remove:
        return pages, 0

    cleaned: list[str] = []
    removed_count = 0
    for page in pages:
        out_lines = []
        for ln in page.splitlines():
            if ln.strip() in to_remove:
                removed_count += 1
                continue
            out_lines.append(ln)
        cleaned.append("\n".join(out_lines))

    return cleaned, removed_count


_EURLEX_PAGE_FOOTNOTE_RE = re.compile(
    r"\(\*+\)\s*Regulation \(EU\) [\d/]+ of the European Parliament[^\n]{0,300}",
    re.MULTILINE,
)


def parse_pdf(path: Path) -> tuple[str, list[int], int, str, list[str]]:
    warnings: list[str] = []
    raw_pages: list[str] = []

    try:
        import pdfplumber
        with pdfplumber.open(str(path)) as pdf:
            for page in pdf.pages:
                raw_pages.append(normalize_text(page.extract_text() or ""))
            page_count = len(pdf.pages)
        parser_name = "pdfplumber"
    except Exception as e:
        warnings.append(f"pdfplumber_failed:{type(e).__name__}")
        log.warning("pdfplumber failed on %s: %s; falling back to pypdf", path.name, e)
        from pypdf import PdfReader
        reader = PdfReader(str(path))
        for page in reader.pages:
            raw_pages.append(normalize_text(page.extract_text() or ""))
        page_count = len(reader.pages)
        parser_name = "pypdf"

    empty_pages = sum(1 for p in raw_pages if not p.strip())
    if empty_pages:
        warnings.append(f"empty_pages:{empty_pages}")

    cleaned_pages, removed_header_lines = _remove_running_headers_footers(raw_pages)
    if removed_header_lines:
        warnings.append(f"removed_repeated_header_footer_lines:{removed_header_lines}")

    cleaned_pages = [_EURLEX_PAGE_FOOTNOTE_RE.sub("", p) for p in cleaned_pages]

    page_breaks: list[int] = []
    text_parts: list[str] = []
    char_pos = 0
    for page_text in cleaned_pages:
        page_text = normalize_text(page_text)
        page_breaks.append(char_pos)
        text_parts.append(page_text)
        char_pos += len(page_text) + 2

    full_text = "\n\n".join(text_parts).strip()
    return full_text, page_breaks, page_count, parser_name, warnings


# ---------------------------------------------------------------------------
# HTML parser
# ---------------------------------------------------------------------------

HTML_STRIP_TAGS = {
    "script", "style", "nav", "noscript", "iframe", "svg", "form",
    "header", "footer", "aside", "button",
}

HTML_BOILERPLATE_HINTS = (
    "cookie", "consent", "navigation", "menu", "sidebar", "breadcrumb",
    "social-share", "related-articles", "footer", "comment", "subscribe",
    "newsletter", "search-bar", "site-header", "advert", "promo",
)

BLOCK_TAGS = [
    "h1", "h2", "h3", "h4", "h5", "h6",
    "p", "li", "article", "section", "div", "blockquote", "table", "tr",
]


def parse_html(path: Path, preserve_hidden: bool = False) -> tuple[str, str, list[str]]:
    from bs4 import BeautifulSoup, Comment

    raw = path.read_bytes()
    html_text, encoding, warnings = detect_encoding(raw)
    soup = BeautifulSoup(html_text, "html.parser")

    removed_tags = 0
    for tag in soup.find_all(HTML_STRIP_TAGS):
        tag.decompose()
        removed_tags += 1
    if removed_tags:
        warnings.append(f"removed_html_tags:{removed_tags}")

    removed_boilerplate = 0
    if not preserve_hidden:
        for tag in soup.find_all(True):
            attrs = " ".join(filter(None, [
                " ".join(tag.get("class", []) or []),
                tag.get("id", "") or "",
            ])).lower()
            if any(hint in attrs for hint in HTML_BOILERPLATE_HINTS):
                tag.decompose()
                removed_boilerplate += 1
    if removed_boilerplate:
        warnings.append(f"removed_boilerplate_nodes:{removed_boilerplate}")

    if preserve_hidden:
        comments_kept = 0
        for comment in soup.find_all(string=lambda t: isinstance(t, Comment)):
            comment.replace_with(f"\n{str(comment)}\n")
            comments_kept += 1
        if comments_kept:
            warnings.append(f"html_comments_preserved:{comments_kept}")

    # Add explicit newlines around block tags so Stage 2 can detect headings/articles better.
    for tag in soup.find_all(BLOCK_TAGS):
        tag.insert_before("\n")
        tag.insert_after("\n")

    text = soup.get_text(separator="\n", strip=True)
    text = normalize_text(text, preserve_newlines=True)

    parser_name = f"beautifulsoup:{encoding}"
    return text, parser_name, warnings


# ---------------------------------------------------------------------------
# Markdown parser
# ---------------------------------------------------------------------------

def parse_md(path: Path) -> tuple[str, str, list[str]]:
    raw = path.read_bytes()
    md_text, encoding, warnings = detect_encoding(raw)
    text = normalize_text(md_text, preserve_newlines=True)
    return text, f"raw_markdown:{encoding}", warnings


# ---------------------------------------------------------------------------
# Manifest + processing
# ---------------------------------------------------------------------------

def load_manifest(path: Path) -> list[dict[str, Any]]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if isinstance(data, list):
        return data
    if isinstance(data, dict) and "entries" in data:
        return data["entries"]
    raise ValueError("Manifest must be either a list or an object with an 'entries' list")


def entry_ext(entry: dict[str, Any], filename: str) -> str:
    ext = (entry.get("ext") or Path(filename).suffix.replace(".", "")).lower()
    if ext == "htm":
        return "html"
    return ext


def process_one(entry: dict[str, Any], raw_dir: Path) -> tuple[Optional[ExtractedDocument], ExtractionEvent]:
    started = perf_counter()
    extracted_at = datetime.now(timezone.utc).isoformat()

    doc_id = entry["doc_id"]
    filename = entry.get("filename") or f"{doc_id}.{entry.get('ext', '')}"
    path = raw_dir / filename
    ext = entry_ext(entry, filename)

    event = ExtractionEvent(
        doc_id=doc_id,
        filename=filename,
        status="started",
        format=ext,
        extracted_at=extracted_at,
    )

    if not path.exists():
        event.status = "missing"
        event.error = f"file_not_found:{path}"
        event.elapsed_ms = int((perf_counter() - started) * 1000)
        log.warning("[missing] %-40s file=%s", doc_id, filename)
        return None, event

    try:
        raw = path.read_bytes()
        sha256 = sha256_of_bytes(raw)
        expected_sha = entry.get("sha256")
        event.bytes = len(raw)
        event.sha256_ok = None if not expected_sha else sha256 == expected_sha

        warnings: list[str] = []
        page_breaks: list[int] = []
        page_count = 0

        if expected_sha and sha256 != expected_sha:
            warnings.append("sha256_mismatch")
            log.warning("sha256 mismatch for %s: file=%s manifest=%s", filename, sha256[:16], expected_sha[:16])

        log.debug("extracting doc_id=%s file=%s ext=%s bytes=%d", doc_id, filename, ext, len(raw))

        if ext == "pdf":
            text, page_breaks, page_count, parser, parser_warnings = parse_pdf(path)
            warnings.extend(parser_warnings)
        elif ext == "html":
            preserve_hidden = entry.get("role") in {"poisoned", "distractor_poisoned"}
            text, parser, parser_warnings = parse_html(path, preserve_hidden=preserve_hidden)
            warnings.extend(parser_warnings)
        elif ext == "md":
            text, parser, parser_warnings = parse_md(path)
            warnings.extend(parser_warnings)
        else:
            raise ValueError(f"unsupported_ext:{ext}")

        char_count = len(text)
        word_count = len(text.split())
        token_count = count_tokens(text)

        if char_count < 200:
            warnings.append("very_short_text")
        if "\ufffd" in text:
            warnings.append("contains_replacement_chars")
        if token_count == 0:
            warnings.append("zero_tokens")

        doc = ExtractedDocument(
            doc_id=doc_id,
            title=entry.get("title", ""),
            url=entry.get("url", ""),
            source_path=str(path),
            filename=filename,
            format=ext,
            doc_type=entry.get("doc_type", entry.get("type", "")),
            tier=entry.get("tier", ""),
            role=entry.get("role", ""),
            parser=parser,
            text=text,
            char_count=char_count,
            word_count=word_count,
            token_count=token_count,
            page_breaks=page_breaks,
            page_count=page_count,
            sha256=sha256,
            bytes=len(raw),
            extracted_at=extracted_at,
            warnings=warnings,
        )

        event.status = "ok"
        event.parser = parser
        event.chars = char_count
        event.words = word_count
        event.tokens = token_count
        event.pages = page_count
        event.warnings = warnings
        event.elapsed_ms = int((perf_counter() - started) * 1000)

        log.info(
            "[ok] %-40s fmt=%-5s tokens=%-7d chars=%-8d pages=%-4d parser=%s%s",
            doc_id, ext, token_count, char_count, page_count, parser,
            f" warnings={warnings}" if warnings else "",
        )
        return doc, event

    except Exception as e:
        event.status = "failed"
        event.error = f"{type(e).__name__}: {e}"
        event.elapsed_ms = int((perf_counter() - started) * 1000)
        log.exception("[failed] %s file=%s", doc_id, filename)
        return None, event


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--manifest", default="data/raw/corpus_manifest.json")
    ap.add_argument("--raw", default="data/raw")
    ap.add_argument("--out", default="data/processed/documents.jsonl")
    ap.add_argument("--stats", default="data/processed/ingestion_stats.json")
    ap.add_argument("--extract-log", default="data/processed/extraction_log.jsonl")
    ap.add_argument("--log-file", default="data/processed/extract.log")
    ap.add_argument("--only", action="append", default=None, help="Process only given doc_id. Can be repeated.")
    ap.add_argument("--verbose", action="store_true")
    args = ap.parse_args()

    setup_logging(Path(args.log_file), verbose=args.verbose)

    manifest_path = Path(args.manifest)
    raw_dir = Path(args.raw)
    out_path = Path(args.out)
    stats_path = Path(args.stats)
    extraction_log_path = Path(args.extract_log)

    if not manifest_path.exists():
        log.error("manifest not found: %s", manifest_path)
        return 1
    if not raw_dir.exists():
        log.error("raw directory not found: %s", raw_dir)
        return 1

    entries = load_manifest(manifest_path)
    if args.only:
        only = set(args.only)
        entries = [e for e in entries if e.get("doc_id") in only]

    out_path.parent.mkdir(parents=True, exist_ok=True)
    stats_path.parent.mkdir(parents=True, exist_ok=True)
    extraction_log_path.parent.mkdir(parents=True, exist_ok=True)

    log.info("starting extraction: docs=%d raw=%s manifest=%s", len(entries), raw_dir, manifest_path)

    docs: list[ExtractedDocument] = []
    events: list[ExtractionEvent] = []

    for entry in entries:
        doc, event = process_one(entry, raw_dir)
        events.append(event)
        if doc is not None:
            docs.append(doc)

    with out_path.open("w", encoding="utf-8") as f:
        for doc in docs:
            f.write(json.dumps(asdict(doc), ensure_ascii=False) + "\n")

    with extraction_log_path.open("w", encoding="utf-8") as f:
        for event in events:
            f.write(json.dumps(asdict(event), ensure_ascii=False) + "\n")

    stats: dict[str, Any] = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "ok": sum(1 for e in events if e.status == "ok"),
        "failed": sum(1 for e in events if e.status == "failed"),
        "missing": sum(1 for e in events if e.status == "missing"),
        "total_documents_in_manifest": len(entries),
        "total_tokens": sum(d.token_count for d in docs),
        "total_chars": sum(d.char_count for d in docs),
        "total_bytes": sum(d.bytes for d in docs),
        "by_format": {},
        "by_tier": {},
        "by_role": {},
        "documents": [],
    }

    for d in docs:
        stats["by_format"][d.format] = stats["by_format"].get(d.format, 0) + 1
        stats["by_tier"][d.tier] = stats["by_tier"].get(d.tier, 0) + 1
        stats["by_role"][d.role] = stats["by_role"].get(d.role, 0) + 1
        stats["documents"].append({
            "doc_id": d.doc_id,
            "title": d.title,
            "format": d.format,
            "tier": d.tier,
            "role": d.role,
            "parser": d.parser,
            "chars": d.char_count,
            "words": d.word_count,
            "tokens": d.token_count,
            "pages": d.page_count,
            "warnings": d.warnings,
        })

    stats_path.write_text(json.dumps(stats, indent=2, ensure_ascii=False), encoding="utf-8")

    log.info("wrote documents: %s", out_path)
    log.info("wrote extraction log: %s", extraction_log_path)
    log.info("wrote stats: %s", stats_path)
    log.info("SUMMARY ok=%d failed=%d missing=%d total_tokens=%s by_format=%s",
             stats["ok"], stats["failed"], stats["missing"], f"{stats['total_tokens']:,}", stats["by_format"])

    return 0 if stats["failed"] == 0 and stats["missing"] == 0 else 2


if __name__ == "__main__":
    raise SystemExit(main())
