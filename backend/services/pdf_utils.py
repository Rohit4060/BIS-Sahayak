"""
Shared PDF text extraction used by all ingestion/metadata code.
Single source of truth — do not duplicate this logic elsewhere.
"""
import re
import pdfplumber

DEVANAGARI_RE = re.compile(r'[\u0900-\u097F]')


def extract_pages(pdf_path):
    """
    Returns list of (page_number, text). Skips pages with no
    extractable English text. Filters out Hindi lines — see note
    in ingest_document.py history for why.
    """
    pages = []
    with pdfplumber.open(pdf_path) as pdf:
        for i, page in enumerate(pdf.pages, start=1):
            raw_text = page.extract_text() or ""
            english_lines = [
                line for line in raw_text.split("\n")
                if not DEVANAGARI_RE.search(line)
            ]
            text = "\n".join(english_lines).strip()
            if not text:
                continue
            pages.append((i, text))
    return pages