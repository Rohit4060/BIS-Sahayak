"""
Product -> Applicable BIS Standards recommender for /api/standards/recommend.

Flow:
  product description
    -> embed + pgvector retrieval, WIDER top_k than /api/chat since we need
       signal across multiple possible standards, not one answer (reuses
       search_service, same embedding model/config as /api/chat and /api/search)
    -> group retrieved chunks by standard (pure Python, no LLM)
    -> Gemini evaluates ONLY the retrieved evidence, per candidate standard,
       and must reference candidates using the exact standard_number strings
       it was given
    -> SAFETY NET: any standard_number in Gemini's output that does not match
       an actually-retrieved candidate is discarded in code, not just by
       prompt instruction — so a hallucinated standard can never reach the user
    -> citations/evidence are built directly from the retrieved chunk rows,
       exactly like rag_service.py — Gemini never produces citations itself
    -> if no candidate clears evaluation, return the honest
       "could not determine" message, never a guess
"""
import json
import os
from collections import defaultdict

from google import genai
from google.genai import types as genai_types
from sqlalchemy.orm import Session

from services.search_service import search_chunks

MODEL_NAME = "gemini-2.5-flash"
TOP_K = 20  # wider than /api/chat's TOP_K=5 — need coverage across standards, not one answer
INSUFFICIENT_EVIDENCE_MSG = (
    "I could not determine an applicable BIS standard from the available BIS sources."
)

client = genai.Client(api_key=os.environ.get("GEMINI_API_KEY"))

SYSTEM_PROMPT = """You are BIS Sahayak AI, evaluating which BIS/Indian Standards
might apply to a product, using ONLY retrieved evidence excerpts grouped by
candidate standard.

You must follow these rules strictly:

1. You will be given a PRODUCT DESCRIPTION, a list of CANDIDATE STANDARDS with
   numbered evidence excerpts under each, and a "valid candidate identifiers"
   list. You may ONLY reference standard_number values that appear EXACTLY in
   that valid identifiers list. Never output a standard_number that is not in
   that list, and never invent a new one.
2. Evaluate relevance using ONLY the supplied evidence. Do not use outside or
   general knowledge about the product or about standards not shown to you.
3. For each candidate standard that has ANY genuine relevance to the product
   description based on the evidence, output an entry with:
   - "standard_number": copied EXACTLY from the valid identifiers list
   - "relevance": "high", "medium", or "low"
   - "reason": a concise explanation grounded in the evidence, referencing
     evidence numbers like [1], [2]
   - "evidence_states_mandatory": true ONLY if the evidence excerpts
     EXPLICITLY state this standard/certification is a mandatory legal
     requirement for this kind of product. Otherwise false. Default to false
     when in doubt — never claim mandatory status the evidence doesn't support.
4. If a candidate standard's evidence is not actually relevant to the product
   description, OMIT it entirely rather than including it with low confidence
   padding.
5. If NONE of the candidate standards are genuinely relevant based on the
   evidence, output an empty "recommendations" list. Do not force a match.
6. Respond with ONLY a JSON object of this exact shape, no other text:
{"recommendations": [{"standard_number": "...", "relevance": "high|medium|low", "reason": "...", "evidence_states_mandatory": true|false}]}
"""


def _group_chunks_by_standard(chunks):
    """Groups retrieved chunks by standard identity. Falls back to document
    title as the grouping key when standard_number wasn't extracted."""
    groups = defaultdict(list)
    for c in chunks:
        key = c["standard_number"] or c["document_title"]
        groups[key].append(c)
    return groups


def _build_evidence_block(groups):
    lines = []
    idx = 1
    for standard_key, chunks in groups.items():
        lines.append(f"=== CANDIDATE STANDARD: {standard_key} ===")
        for c in chunks:
            lines.append(
                f"[{idx}] Section: {c['section']} | Page: {c['page_number']}\n{c['chunk_text']}"
            )
            idx += 1
        lines.append("")
    return "\n".join(lines)


def _build_citations_for_group(chunks):
    """Built directly from retrieved chunks only — never from Gemini's output."""
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


def _build_evidence_list_for_group(chunks):
    """Human-readable evidence excerpts for the response payload — again built
    from DB rows only."""
    seen = set()
    evidence = []
    for c in chunks:
        key = (c["section"], c["page_number"])
        if key in seen:
            continue
        seen.add(key)
        excerpt = c["chunk_text"]
        if len(excerpt) > 300:
            excerpt = excerpt[:300] + "..."
        evidence.append({
            "section": c["section"],
            "page": c["page_number"],
            "excerpt": excerpt,
        })
    return evidence


def recommend_standards(db: Session, product_description: str):
    """
    Returns {"product_description": str, "recommendations": list[dict]} where
    each recommendation has standard_number, title, relevance, reason,
    requirement_status, evidence, and citations.
    If no evidence-backed candidate survives evaluation, "recommendations" is
    an empty list and "message" carries the honest insufficient-evidence note.
    Raises on embedding/database/Gemini failure — caller (route) handles it,
    same convention as get_rag_response.
    """
    chunks = search_chunks(db, product_description, top_k=TOP_K)

    if not chunks:
        return {
            "product_description": product_description,
            "recommendations": [],
            "message": INSUFFICIENT_EVIDENCE_MSG,
        }

    groups = _group_chunks_by_standard(chunks)
    valid_keys = list(groups.keys())

    evidence_block = _build_evidence_block(groups)
    user_message = (
        f"PRODUCT DESCRIPTION: {product_description}\n\n"
        f"{evidence_block}\n"
        f"Valid candidate standard identifiers (use EXACTLY these strings, nothing else): "
        f"{json.dumps(valid_keys)}"
    )

    response = client.models.generate_content(
        model=MODEL_NAME,
        contents=user_message,
        config=genai_types.GenerateContentConfig(
            system_instruction=SYSTEM_PROMPT,
            max_output_tokens=1500,
            response_mime_type="application/json",
            temperature=0.1,  # low temperature: this is an evidence-grounded relevance
                               # judgment, not creative writing — should be consistent
                               # across repeated calls on the same evidence
        ),
    )

    try:
        parsed = json.loads(response.text)
        gemini_recs = parsed.get("recommendations", [])
    except (json.JSONDecodeError, AttributeError, TypeError):
        gemini_recs = []

    recommendations = []
    for rec in gemini_recs:
        standard_key = rec.get("standard_number")

        # SAFETY NET: enforced in code, not just the prompt. A standard_number
        # that wasn't actually retrieved can never reach the user, no matter
        # what Gemini outputs.
        if standard_key not in groups:
            continue

        relevance = rec.get("relevance")
        if relevance not in ("high", "medium", "low"):
            relevance = "low"

        group_chunks = groups[standard_key]
        evidence_states_mandatory = bool(rec.get("evidence_states_mandatory", False))

        recommendations.append({
            "standard_number": group_chunks[0]["standard_number"],
            "title": group_chunks[0]["document_title"],
            "relevance": relevance,
            "reason": rec.get("reason", ""),
            "requirement_status": (
                "Evidence explicitly indicates a mandatory requirement."
                if evidence_states_mandatory
                else "Potentially applicable — not a confirmed mandatory requirement "
                     "based on currently available evidence."
            ),
            "evidence": _build_evidence_list_for_group(group_chunks),
            "citations": _build_citations_for_group(group_chunks),
        })

    if not recommendations:
        return {
            "product_description": product_description,
            "recommendations": [],
            "message": INSUFFICIENT_EVIDENCE_MSG,
        }

    return {
        "product_description": product_description,
        "recommendations": recommendations,
    }