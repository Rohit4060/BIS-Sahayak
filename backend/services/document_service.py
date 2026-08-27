"""
Document processing service — SKELETON ONLY.

This module will eventually handle:
- Reading raw BIS documents from data/raw/
- Splitting documents into chunks (by page/section/clause)
- Generating embeddings for each chunk
- Saving processed documents into data/processed/
- Writing Document and DocumentChunk records to the database

None of that is implemented yet. This file exists now so the project
structure is ready for the next milestone.
"""

from sqlalchemy.orm import Session
from models import Document, DocumentChunk


def create_document_record(
    db: Session,
    title: str,
    document_type: str | None = None,
    standard_number: str | None = None,
    version: str | None = None,
    source_url: str | None = None,
    file_name: str | None = None,
) -> Document:
    """
    Creates a Document row with no chunks yet.
    Useful for testing the database models before real ingestion exists.
    """
    doc = Document(
        title=title,
        document_type=document_type,
        standard_number=standard_number,
        version=version,
        source_url=source_url,
        file_name=file_name,
    )
    db.add(doc)
    db.commit()
    db.refresh(doc)
    return doc