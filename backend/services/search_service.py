"""
Retrieval/search service.

Given a user query:
1. Embeds the query using the SAME Gemini embedding model used at ingestion
   (task_type differs: RETRIEVAL_QUERY here vs RETRIEVAL_DOCUMENT at ingestion —
   this is Gemini's recommended pairing for accurate retrieval).
2. Runs a pgvector cosine-similarity search against document_chunks.embedding.
3. Returns the top matching chunks with full citation metadata.

Does NOT call Gemini to generate an answer. Pure retrieval only.
"""
import os
import re
import unicodedata

from google import genai
from google.genai import types as genai_types
from sqlalchemy.orm import Session

from models import Document, DocumentChunk

EMBEDDING_MODEL = "gemini-embedding-001"
EMBEDDING_DIM = 768
# The current populated KB's live retrieval audit found IS 302 to be the top
# result for "electric pressure cooker" at 0.5874 and "pressure cooker" at
# 0.5832. The unrelated "titanium spacecraft heat shield" control peaked at
# 0.5690. Keep a small evidence-floor margin: this admits the existing IS 302
# household-appliance evidence while preserving the unrelated-query fallback.
MIN_RELEVANCE_SCORE = 0.58

client = genai.Client(api_key=os.environ.get("GEMINI_API_KEY"))

# An explicit identifier is authoritative user input, not an inferred standard.
# Keep only its stable ``IS <number>`` stem for database matching: document
# metadata can include punctuation, a Part, a year, or an IEC cross-reference.
# We never manufacture or rewrite an identifier for display or citations.
IS_IDENTIFIER_PATTERN = re.compile(
    r"\bIS\s*[-:]?\s*(\d{2,6})\b", re.IGNORECASE
)


def normalize_query(query: str) -> str:
    """Apply only Unicode/whitespace normalisation before embedding/searching.

    This preserves the language and wording of the question while preventing
    inconsequential formatting differences from affecting retrieval.
    """
    return " ".join(unicodedata.normalize("NFKC", query).split())


def extract_explicit_standard_identifier(query: str) -> str | None:
    """Return an explicitly supplied ``IS <number>`` stem, if present.

    The value is used solely as a metadata filter. It is deliberately derived
    from the user's text and is never returned as a generated identifier.
    """
    match = IS_IDENTIFIER_PATTERN.search(query)
    return f"IS {match.group(1)}" if match else None


def _deduplicate_candidate_rows(rows, top_k: int):
    """Keep evidence diverse without changing its rank or provenance.

    Ingested PDFs can yield several chunks for the same page/section. Passing
    all of them to Gemini crowds out distinct evidence, so retain the first
    (highest-ranked) candidate per document/page/section. Exact duplicate
    text is also kept only once even if its metadata differs.
    """
    selected = []
    seen_locations = set()
    seen_texts = set()
    for chunk, document, distance in rows:
        location_key = (document.id, chunk.page_number, chunk.section)
        text_key = " ".join(chunk.chunk_text.lower().split())
        if location_key in seen_locations or text_key in seen_texts:
            continue
        seen_locations.add(location_key)
        seen_texts.add(text_key)
        selected.append((chunk, document, distance))
        if len(selected) == top_k:
            break
    return selected


def embed_query(query: str):
    """Embeds a search query. Raises on failure — caller handles it."""
    response = client.models.embed_content(
        model=EMBEDDING_MODEL,
        contents=query,
        config=genai_types.EmbedContentConfig(
            task_type="RETRIEVAL_QUERY",
            output_dimensionality=EMBEDDING_DIM,
        ),
    )
    return response.embeddings[0].values


def search_chunks(db: Session, query: str, top_k: int = 5):
    """
    Returns a list of dicts, ranked by relevance, each containing full
    citation metadata for a matching chunk.
    """
    normalized_query = normalize_query(query)
    query_embedding = embed_query(normalized_query)

    # pgvector cosine_distance: 0 = identical, 2 = opposite.
    # We convert to a more intuitive "relevance_score" where higher = more relevant.
    distance = DocumentChunk.embedding.cosine_distance(query_embedding)

    # Retrieve a small wider pool first. This gives the deterministic
    # de-duplicator enough candidates to replace repeated page/section chunks
    # while leaving ranking and all citation metadata DB-derived.
    candidate_limit = min(max(top_k * 3, top_k), 60)
    query_rows = (
        db.query(DocumentChunk, Document, distance.label("distance"))
        .join(Document, DocumentChunk.document_id == Document.id)
        .filter(DocumentChunk.embedding.isnot(None))
        .order_by(distance)
    )

    explicit_identifier = extract_explicit_standard_identifier(normalized_query)
    if explicit_identifier:
        # This only narrows results to documents whose stored metadata contains
        # the identifier the user actually typed. An unknown identifier safely
        # produces no evidence rather than a semantic near-match.
        query_rows = query_rows.filter(Document.standard_number.ilike(f"%{explicit_identifier}%"))

    rows = _deduplicate_candidate_rows(query_rows.limit(candidate_limit).all(), top_k)

    results = []
    for chunk, document, dist in rows:
        relevance_score = round(1 - float(dist), 4)
        if relevance_score < MIN_RELEVANCE_SCORE:
            continue
        results.append({
            "relevance_score": relevance_score,
            "standard_number": document.standard_number,
            "document_title": document.title,
            "page_number": chunk.page_number,
            "section": chunk.section,
            "chunk_text": chunk.chunk_text,
            "source_url": document.source_url,
        })
    return results
