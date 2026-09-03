"""Regression tests for the shared M16 ingestion and citation pipeline."""

from scripts.ingest_document import build_chunks
from services.rag_service import _build_citations


def test_clause_aware_chunking_preserves_page_and_section_metadata():
    pages = [
        (1, "1. General\n" + "A" * 240),
        (2, "Cl. 2 Requirements\n" + "B" * 240),
    ]

    chunks = build_chunks(pages)

    assert len(chunks) == 2
    assert chunks[0]["page"] == 1
    assert chunks[0]["section"] == "1. General"
    assert chunks[1]["page"] == 2
    assert chunks[1]["section"] == "Cl. 2 Requirements"


def test_multi_document_citations_keep_the_retrieved_source_metadata():
    chunks = [
        {
            "standard_number": "IS 1417 : 2016",
            "section": "2. Hallmarking",
            "page_number": 2,
            "source_url": "https://www.bis.gov.in/example-hallmarking.pdf",
        },
        {
            "standard_number": None,
            "section": "1. INTRODUCTION",
            "page_number": 5,
            "source_url": "https://www.bis.gov.in/example-complaints.pdf",
        },
    ]

    citations = _build_citations(chunks)

    assert citations == [
        {
            "standard_number": "IS 1417 : 2016",
            "clause": "2. Hallmarking",
            "page": 2,
            "source_url": "https://www.bis.gov.in/example-hallmarking.pdf",
        },
        {
            "standard_number": None,
            "clause": "1. INTRODUCTION",
            "page": 5,
            "source_url": "https://www.bis.gov.in/example-complaints.pdf",
        },
    ]
