"""
RAG (Retrieval-Augmented Generation) service for /api/chat.

Flow:
  user question
    -> embed query + pgvector similarity search (reuses search_service)
    -> top BIS chunks given to Gemini as evidence
    -> Gemini answers using ONLY that evidence
    -> structured citations built directly from the retrieved chunks
       (never parsed from Gemini's text, so citations can never be invented)
"""
import os

from google import genai
from google.genai import types as genai_types
from sqlalchemy.orm import Session

from services.search_service import search_chunks

MODEL_NAME = "gemini-2.5-flash"
TOP_K = 5
INSUFFICIENT_EVIDENCE_MSG = "I could not verify this from the available BIS sources."

client = genai.Client(api_key=os.environ.get("GEMINI_API_KEY"))

SYSTEM_PROMPT = """You are BIS Sahayak AI, an assistant for Indian Standards (IS) and
Bureau of Indian Standards (BIS) compliance topics.

You will be given a user question along with numbered EVIDENCE excerpts retrieved
from official BIS documents. You must follow these rules strictly:

1. Answer using ONLY the supplied evidence excerpts below. Do not use outside or
   general knowledge, even if you believe you know the answer.
2. Never invent, guess, or assume standards, clause numbers, schemes, requirements,
   or citations that are not explicitly present in the evidence.
3. When you state a fact, reference which evidence excerpt it came from using its
   [number], e.g. "Marking is mandatory on the product and packaging [1]."
4. If the evidence does not contain enough information to answer the question,
   you must respond with exactly this sentence:
   "I could not verify this from the available BIS sources."
   You may briefly note what the available evidence does cover, if anything, but
   you must not fill the gap with general knowledge.
5. Clearly distinguish between what the evidence explicitly states and anything
   that is ambiguous or only partially covered.

Be clear and concise."""


def _build_evidence_block(chunks):
    lines = []
    for i, c in enumerate(chunks, start=1):
        lines.append(
            f"[{i}] Standard: {c['standard_number']} | Section: {c['section']} | "
            f"Page: {c['page_number']}\n{c['chunk_text']}"
        )
    return "\n\n".join(lines)


def _build_citations(chunks):
    """Built directly from retrieved chunks only — never from Gemini's output —
    so a citation can never be something the model invented."""
    seen = set()
    citations = []
    for c in chunks:
        key = (c["standard_number"], c["section"], c["page_number"])
        if key in seen:
            continue
        seen.add(key)
        citations.append({
            "standard_number": c["standard_number"],
            "clause": c["section"],
            "page": c["page_number"],
            "source_url": c["source_url"],
        })
    return citations


def format_citation_footer(citations):
    """Human-readable 'Sources:' block appended to the reply text, so the
    citations are visible in the current UI without any frontend changes."""
    if not citations:
        return ""
    lines = ["", "Sources:"]
    for i, c in enumerate(citations, start=1):
        parts = []
        if c["standard_number"]:
            parts.append(c["standard_number"])
        if c["clause"]:
            parts.append(c["clause"])
        if c["page"]:
            parts.append(f"page {c['page']}")
        line = f"[{i}] " + ", ".join(parts)
        if c["source_url"]:
            line += f" ({c['source_url']})"
        lines.append(line)
    return "\n".join(lines)


def get_rag_response(db: Session, question: str):
    """
    Returns {"answer": str, "citations": list[dict]}.
    Raises on embedding/database/Gemini failure — caller handles it.
    """
    chunks = search_chunks(db, question, top_k=TOP_K)

    if not chunks:
        return {"answer": INSUFFICIENT_EVIDENCE_MSG, "citations": []}

    evidence_block = _build_evidence_block(chunks)
    user_message = f"QUESTION: {question}\n\nEVIDENCE EXCERPTS:\n{evidence_block}"

    response = client.models.generate_content(
        model=MODEL_NAME,
        contents=user_message,
        config=genai_types.GenerateContentConfig(
            system_instruction=SYSTEM_PROMPT,
            max_output_tokens=1000,
        ),
    )

    return {"answer": response.text, "citations": _build_citations(chunks)}