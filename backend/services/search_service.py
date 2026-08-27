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

from google import genai
from google.genai import types as genai_types
from sqlalchemy.orm import Session

from models import Document, DocumentChunk

EMBEDDING_MODEL = "gemini-embedding-001"
EMBEDDING_DIM = 768

client = genai.Client(api_key=os.environ.get("GEMINI_API_KEY"))


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
    query_embedding = embed_query(query)

    # pgvector cosine_distance: 0 = identical, 2 = opposite.
    # We convert to a more intuitive "relevance_score" where higher = more relevant.
    distance = DocumentChunk.embedding.cosine_distance(query_embedding)

    rows = (
        db.query(DocumentChunk, Document, distance.label("distance"))
        .join(Document, DocumentChunk.document_id == Document.id)
        .order_by(distance)
        .limit(top_k)
        .all()
    )

    results = []
    for chunk, document, dist in rows:
        relevance_score = round(1 - float(dist), 4)
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