"""
Deterministic metadata extraction for BIS PDF documents.

No LLM calls. No guessing. If something cannot be confidently
detected, it is left as None and a warning is recorded — never
invented.
"""
import re
from pathlib import Path

STANDARD_NUMBER_RE = re.compile(
    r'\bIS\s+\d{2,6}(?:\s*\(\s*Part\s*\d+\s*\))?\s*:\s*\d{4}'
    r'(?:\s*/\s*IEC\s*\d{4,6}(?:-\d+)?\s*:\s*\d{4})?',
    re.IGNORECASE,
)

REVISION_RE = re.compile(
    r'\b(First|Second|Third|Fourth|Fifth|Sixth|Seventh|Eighth|Ninth|Tenth)\s+Revision\b'
    r'(?:\s*,?\s*([A-Z][a-z]+\s+\d{4}))?',
)

URL_RE = re.compile(r'https?://(?:www\.)?bis\.gov\.in[^\s)"\']*', re.IGNORECASE)

TITLE_BLOCKLIST = [
    "bureau of indian standards",
    "manak bhawan",
    "bahadur shah zafar marg",
    "new delhi",
    "product manual",
    "document no",
    "this product manual",
    "this document",
    "for the purpose of",
    "free standard provided by",
    "bsb edge",
]

EXACT_BLOCKLIST = {
    "indian standard",
    "draft indian standard",
    "specification",
    "first revision",
    "second revision",
    "third revision",
}


def _is_title_like(line):
    lower = line.lower().strip(" —-:()")
    if lower in EXACT_BLOCKLIST:
        return False
    if any(b in lower for b in TITLE_BLOCKLIST):
        return False
    if STANDARD_NUMBER_RE.search(line):
        return False
    words = [w for w in re.split(r'\s+', line) if w.isalpha()]
    if len(words) < 2:
        return False
    capitalized = sum(1 for w in words if w[0].isupper())
    ratio = capitalized / len(words)
    return ratio >= 0.6


def _find_title_block(text):
    """
    Finds a run of consecutive title-like lines (a heading that may
    span multiple lines) and joins them into one title string.
    """
    lines = [l.strip() for l in text.split("\n") if l.strip()]
    best_block = None
    i = 0
    while i < len(lines):
        if _is_title_like(lines[i]):
            block = [lines[i]]
            j = i + 1
            while j < len(lines) and _is_title_like(lines[j]) and len(" ".join(block)) < 150:
                block.append(lines[j])
                j += 1
            joined = " ".join(block).strip()
            if 15 <= len(joined) <= 200:
                if best_block is None or len(joined) > len(best_block):
                    best_block = joined
            i = j
        else:
            i += 1
    return best_block


def extract_metadata(pdf_path: Path, pages: list[tuple[int, str]]) -> dict:
    """
    pages: list of (page_number, text) — already Devanagari-filtered,
    from services.pdf_utils.extract_pages.

    Returns a dict with standard_number, title, version, source_url,
    and warnings. Anything not confidently found is None.
    """
    warnings = []

    scan_pages = pages[:2]
    combined_text = "\n".join(text for _, text in scan_pages)
    first_page_text = pages[0][1] if pages else ""

    standard_number = None
    match = STANDARD_NUMBER_RE.search(combined_text)
    if match:
        standard_number = " ".join(match.group(0).split())
    else:
        warnings.append("standard_number: no 'IS <number> : <year>' pattern found on first 2 pages")

    version = None
    match = REVISION_RE.search(combined_text)
    if match:
        revision_word = match.group(1)
        date_part = match.group(2)
        version = f"{revision_word} Revision" + (f", {date_part}" if date_part else "")
    else:
        warnings.append("version: no '<Nth> Revision' pattern found on first 2 pages")

    title = _find_title_block(first_page_text)
    if not title:
        warnings.append("title: could not confidently identify a title block on page 1")

    source_url = None
    match = URL_RE.search(combined_text)
    if match:
        source_url = match.group(0).rstrip(').,')
    else:
        warnings.append("source_url: no bis.gov.in URL found in document text (will store None — never fabricated)")

    return {
        "standard_number": standard_number,
        "title": title,
        "version": version,
        "source_url": source_url,
        "warnings": warnings,
    }