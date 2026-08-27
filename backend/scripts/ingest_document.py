"""
Ingests a single BIS PDF document into the database:
- extracts text per page
- detects clause/section headings
- creates clause-aware chunks (not fixed-character splitting)
- generates embeddings via Gemini
- stores Document + DocumentChunk records in Postgres/pgvector

Usage (run from the backend/ folder, with venv active):
    python scripts/ingest_document.py "../data/raw/IS_302_Part1_Household_Appliances_Safety.pdf"
"""
import argparse
import os
import re
import sys
import time
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parent.parent))  # so "database"/"models" import cleanly

from services.pdf_utils import extract_pages
from services.metadata_extractor import extract_metadata

from dotenv import load_dotenv
load_dotenv()

import pdfplumber
from google import genai
from google.genai import types as genai_types

from database import SessionLocal
from models import Document, DocumentChunk

EMBEDDING_MODEL = "gemini-embedding-001"
EMBEDDING_DIM = 768
CHUNK_MAX_CHARS = 1200
CHUNK_MIN_CHARS = 200

gemini_client = genai.Client(api_key=os.environ.get("GEMINI_API_KEY"))

HEADING_PATTERNS = [
    re.compile(r'^\s*ANNEX\s*[–-]\s*[A-Z]', re.IGNORECASE),
    re.compile(r'^\s*\d{1,2}\.\s+[A-Za-z]'),       # e.g. "1. Sample Guidelines"
    re.compile(r'^\s*Cl\.\s*\d+', re.IGNORECASE),   # e.g. "Cl. 8 Protection..."
]
DEVANAGARI_RE = re.compile(r'[\u0900-\u097F]')


def log(msg):
    print(f"[ingest] {msg}")





def detect_heading(line):
    line = line.strip()
    for pattern in HEADING_PATTERNS:
        if pattern.match(line):
            return line[:150]
    return None


def build_chunks(pages):
    """
    Walks through pages line by line, tracking the most recent detected
    clause/section heading. Starts a new chunk whenever a heading is found,
    and otherwise groups lines up to CHUNK_MAX_CHARS — never blindly
    splitting mid-sentence at a fixed character count.
    Returns list of dicts: {text, page, section}
    """
    chunks = []
    current_section = None
    buffer_lines = []
    buffer_page_start = None

    def flush():
        nonlocal buffer_lines, buffer_page_start
        if buffer_lines:
            text = "\n".join(buffer_lines).strip()
            if len(text) >= CHUNK_MIN_CHARS or not chunks:
                chunks.append({"text": text, "page": buffer_page_start, "section": current_section})
            elif chunks:
                chunks[-1]["text"] += "\n" + text
        buffer_lines = []
        buffer_page_start = None

    for page_num, page_text in pages:
        for line in page_text.split("\n"):
            heading = detect_heading(line)
            if heading:
                flush()
                current_section = heading

            if buffer_page_start is None:
                buffer_page_start = page_num
            buffer_lines.append(line)

            if len("\n".join(buffer_lines)) >= CHUNK_MAX_CHARS:
                flush()

    flush()
    return [c for c in chunks if c["text"]]


def embed_text(text):
    """Calls Gemini embeddings API. Raises on failure — caller handles it."""
    response = gemini_client.models.embed_content(
        model=EMBEDDING_MODEL,
        contents=text,
        config=genai_types.EmbedContentConfig(
            task_type="RETRIEVAL_DOCUMENT",
            output_dimensionality=EMBEDDING_DIM,
        ),
    )
    return response.embeddings[0].values


def ingest(pdf_path_str, title, standard_number, version, source_url, document_type="Product Manual"):
    pdf_path = Path(pdf_path_str)
    if not pdf_path.exists():
        log(f"ERROR: file not found: {pdf_path}")
        sys.exit(1)
    if pdf_path.suffix.lower() != ".pdf":
        log(f"ERROR: not a PDF file: {pdf_path}")
        sys.exit(1)

    file_name = pdf_path.name
    log(f"document detected: {file_name}")

    try:
        pages = extract_pages(pdf_path)
    except Exception as e:
        log(f"ERROR: failed to read PDF (invalid or corrupt file?): {e}")
        sys.exit(1)

    if not pages:
        log("ERROR: no extractable text found (this may be a scanned image PDF). Aborting.")
        sys.exit(1)
    log(f"pages processed: {len(pages)}")

    chunks = build_chunks(pages)
    if not chunks:
        log("ERROR: no chunks could be built from this document. Aborting.")
        sys.exit(1)
    log(f"chunks created: {len(chunks)}")

    db = SessionLocal()
    try:
        # Idempotency: if this file was already ingested, remove the old
        # document (and its chunks, via cascade) before re-inserting fresh.
        existing = db.query(Document).filter(Document.file_name == file_name).first()
        if existing:
            log(f"existing document found for '{file_name}' (id={existing.id}) — replacing it")
            db.delete(existing)
            db.commit()

        document = Document(
            title=title,
            document_type=document_type,
            standard_number=standard_number,
            version=version,
            source_url=source_url,
            file_name=file_name,
        )
        db.add(document)
        db.commit()
        db.refresh(document)
        log(f"database record inserted: document id={document.id}")

        embedded_count = 0
        for idx, chunk in enumerate(chunks, start=1):
            try:
                embedding = embed_text(chunk["text"])
            except Exception as e:
                log(f"  chunk {idx}/{len(chunks)}: EMBEDDING FAILED ({e}) — skipping this chunk")
                continue

            db.add(DocumentChunk(
                document_id=document.id,
                chunk_text=chunk["text"],
                page_number=chunk["page"],
                section=chunk["section"],
                embedding=embedding,
            ))
            embedded_count += 1

            if idx % 5 == 0 or idx == len(chunks):
                log(f"  embedded {idx}/{len(chunks)} chunks so far")

            time.sleep(0.2)  # gentle pacing for API rate limits

        db.commit()
        log(f"embeddings generated: {embedded_count}/{len(chunks)}")
        log(f"database records inserted: {embedded_count} chunk rows -> document id={document.id}")
        log("DONE.")

    except Exception as e:
        db.rollback()
        log(f"ERROR: database failure during ingestion: {e}")
        sys.exit(1)
    finally:
        db.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Ingest a single BIS PDF into the database.")
    parser.add_argument("pdf_path", help="Path to the PDF file to ingest")
    parser.add_argument("--title", default=None, help="Override auto-detected title")
    parser.add_argument("--standard-number", default=None, help="Override auto-detected standard number")
    parser.add_argument("--version", default=None, help="Override auto-detected version")
    parser.add_argument("--source-url", default=None, help="Override auto-detected source URL (never guessed)")
    parser.add_argument("--document-type", default="Standard")
    args = parser.parse_args()

    pdf_path = Path(args.pdf_path)
    pages_for_metadata = extract_pages(pdf_path)
    detected = extract_metadata(pdf_path, pages_for_metadata)

    for warning in detected["warnings"]:
        log(f"METADATA WARNING: {warning}")

    final_title = args.title or detected["title"]
    final_standard_number = args.standard_number or detected["standard_number"]
    final_version = args.version or detected["version"]
    final_source_url = args.source_url or detected["source_url"]

    if not final_title:
        log("METADATA WARNING: title is unknown — storing NULL, not inventing one")
    if not final_standard_number:
        log("METADATA WARNING: standard_number is unknown — storing NULL, not inventing one")

    ingest(
        pdf_path_str=args.pdf_path,
        title=final_title,
        standard_number=final_standard_number,
        version=final_version,
        source_url=final_source_url,
        document_type=args.document_type,
    )