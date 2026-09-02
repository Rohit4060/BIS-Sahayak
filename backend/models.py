import uuid
from datetime import datetime, timezone

from sqlalchemy import Column, String, Text, Integer, ForeignKey, DateTime
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from pgvector.sqlalchemy import Vector

from database import Base

# Gemini's text-embedding model outputs 768-dimensional vectors.
# We're only declaring the column shape now — no embeddings are created yet.
EMBEDDING_DIM = 768


class Document(Base):
    __tablename__ = "documents"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    title = Column(String, nullable=False)
    document_type = Column(String, nullable=True)      # e.g. "Indian Standard", "Guideline"
    standard_number = Column(String, nullable=True)     # e.g. "IS 302"
    version = Column(String, nullable=True)              # e.g. "3rd Revision, 2019"
    source_url = Column(String, nullable=True)
    file_name = Column(String, nullable=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    chunks = relationship("DocumentChunk", back_populates="document", cascade="all, delete-orphan")


class DocumentChunk(Base):
    __tablename__ = "document_chunks"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    document_id = Column(UUID(as_uuid=True), ForeignKey("documents.id"), nullable=False)
    chunk_text = Column(Text, nullable=False)
    page_number = Column(Integer, nullable=True)
    section = Column(String, nullable=True)              # clause/section reference
    embedding = Column(Vector(EMBEDDING_DIM), nullable=True)

    document = relationship("Document", back_populates="chunks")



class Laboratory(Base):
    """
    Stores authoritative BIS-recognized/NABL-accredited testing laboratory
    information for the Laboratory Finder (/api/labs/find).

    NOTE: As of Milestone 12, this table has NO ingestion pipeline yet — it
    is intentionally empty until authoritative laboratory data (e.g. from
    BIS's official recognized-labs list) is sourced and loaded. Until then,
    /api/labs/find will correctly return an insufficient-evidence response
    for every query, which is the safe and honest behavior.

    Future ingestion will need, per laboratory entry:
      - name (required)
      - location/address
      - capabilities (what kinds of tests it can perform)
      - standard_numbers (which IS/BIS standards it's recognized for)
      - accreditation info (e.g. "NABL accredited per IS/ISO/IEC 17025",
        "BIS recognized/empanelled") — only ever populated from a source
        document that explicitly states this, never inferred
      - source_url / source_reference (where this info was sourced from,
        for citation purposes)
    """
    __tablename__ = "laboratories"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String, nullable=False)
    location = Column(String, nullable=True)
    capabilities = Column(Text, nullable=True)            # free text or comma-separated
    standard_numbers = Column(Text, nullable=True)         # comma-separated IS numbers, e.g. "IS 302 (Part 1) : 2024, IS 17423 : 2021"
    accreditation_info = Column(Text, nullable=True)       # e.g. "NABL accredited per IS/ISO/IEC 17025"
    source_url = Column(String, nullable=True)
    source_reference = Column(String, nullable=True)       # e.g. document title/page this was sourced from
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))