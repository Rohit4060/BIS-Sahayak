"""
Consumer Assistant for /api/consumer/help.

Flow:
  consumer question
    -> embed + pgvector retrieval (reuses search_service, identical to
       hallmarking_service.py / rag_service.py — no duplicated
       embedding/search logic)
    -> Gemini answers ONLY from the retrieved evidence and must self-report
       whether its answer asserts a mandatory/legal, certification, safety,
       or legality claim, and which evidence numbers each key point / next
       step is grounded in
    -> SAFETY NET 1: any evidence index Gemini references that wasn't
       actually retrieved is discarded in code
    -> SAFETY NET 2: any IS/standard number mentioned anywhere in Gemini's
       text output that doesn't match an actually-retrieved standard_number
       is treated as a hallucinated standard and rejects the response
    -> SAFETY NET 3: mandatory/legal claims are never taken on Gemini's word
       alone — reuses MANDATORY_KEYWORDS from hallmarking_service.py rather
       than duplicating that list a third time
    -> SAFETY NET 4: certification / safety / legality claims about a
       product ("is certified", "is safe", "is illegal", etc.) are likewise
       rejected unless the raw retrieved evidence text itself contains
       matching language — this is Consumer Assistant-specific, since
       M13/M11 never needed to guard these claim types
    -> citations are built directly from retrieved chunk rows, never from
       Gemini's own text
    -> if no evidence, or the response fails a safety net, return the honest
       "could not verify" message, never a guess

This module deliberately does NOT hard-code any BIS certification details,
product-safety judgments, legal conclusions, or complaint/contact
information from general knowledge. All such specifics must come from
retrieved evidence, or the assistant refuses.
"""
import json
import os
import re

from google import genai
from google.genai import types as genai_types
from sqlalchemy.orm import Session

from services.search_service import search_chunks
from services.hallmarking_service import MANDATORY_KEYWORDS, IS_NUMBER_PATTERN

MODEL_NAME = "gemini-2.5-flash"
TOP_K = 8

INSUFFICIENT_EVIDENCE_MSG = "I could not verify this from the available BIS sources."
INSUFFICIENT_EVIDENCE_LIMITATION = (
    "The available BIS sources did not contain enough information to answer this question."
)

STATUS_SUPPORTED = "supported_by_evidence"
STATUS_INSUFFICIENT = "insufficient_evidence"

# Consumer Assistant-specific claim categories, beyond the mandatory/legal
# guard already established in M11/M13. Each category is checked the same
# way: if Gemini's output asserts a claim in this category, the RAW
# retrieved evidence text must itself contain matching language, or the
# whole response is rejected.
CERTIFICATION_KEYWORDS = [
    "certified",
    "certification",
    "bis certified",
    "bis approved",
    "holds a valid license",
    "carries the bis mark",
]
SAFETY_KEYWORDS = [
    "is safe",
    "safe to use",
    "unsafe",
    "not safe",
    "hazardous",
    "dangerous to use",
]
LEGALITY_KEYWORDS = [
    "illegal",
    "unlawful",
    "violates the law",
    "against the law",
    "in violation of",
    "breaking the law",
]

CLAIM_CATEGORIES = {
    "mandatory": MANDATORY_KEYWORDS,
    "certification": CERTIFICATION_KEYWORDS,
    "safety": SAFETY_KEYWORDS,
    "legality": LEGALITY_KEYWORDS,
}

client = genai.Client(api_key=os.environ.get("GEMINI_API_KEY"))

SYSTEM_PROMPT = """You are BIS Sahayak AI, helping everyday consumers understand
BIS-related questions using ONLY retrieved evidence excerpts from official BIS
documents. This is a consumer help tool, not a general chatbot — stay
strictly within what the evidence supports.

You must follow these rules strictly:

1. Answer using ONLY the supplied numbered EVIDENCE excerpts. Do not use
   outside or general knowledge, even if you believe you know the answer.
2. NEVER invent or assume: IS numbers, clauses, BIS requirements,
   certification requirements, legal obligations, complaint procedures,
   BIS services, URLs, or citations. If it is not explicitly in the
   evidence, do not state it.
3. Only mention a standard number (e.g. "IS 1417") if it appears verbatim in
   the evidence excerpts you were given. Never write a standard number from
   memory.
4. Every key point and next step must be traceable to specific evidence
   excerpt numbers, referenced as "evidence_refs": [1, 2] (the numbers
   correspond to the [N] markers in the evidence block). Never invent a
   next step or procedure that is not itself grounded in the evidence.
5. Distinguish carefully between the evidence saying something is
   "applicable", "recommended", or "may apply" versus explicitly stating it
   is "mandatory" or a "legal requirement". Do NOT upgrade the former into
   the latter.
6. NEVER state or imply that a specific product is BIS certified, that BIS
   certification is mandatory for a product, that a product is safe or
   unsafe, or that a product or seller is acting illegally — UNLESS the
   evidence excerpts explicitly say so. If the evidence only discusses BIS
   processes/marks in general, do not apply that generally to the
   consumer's specific product as a factual claim.
7. Set each of the following flags to true ONLY if the evidence excerpts
   themselves explicitly support that kind of claim for what you are
   telling the user; otherwise false. Default to false when uncertain.
   - "asserts_mandatory": a legal/mandatory requirement
   - "asserts_certification_claim": that a product/seller is or isn't BIS
     certified
   - "asserts_safety_claim": that a product is safe or unsafe
   - "asserts_legality_claim": that something is legal or illegal
8. If the evidence does not contain enough information to answer the
   question, set "status" to "insufficient_evidence", set "answer" to
   exactly "I could not verify this from the available BIS sources.", and
   leave "key_points" and "next_steps" empty. Do not fill the gap with
   general knowledge.
9. Use simple, everyday language a non-technical consumer can follow. Avoid
   unexplained jargon; briefly explain any BIS-specific term you must use.
   Separate what is factually established from anything uncertain. Avoid
   legal-advice phrasing (e.g. do not say "you should sue" or "you are
   entitled to compensation") — only what the evidence itself states.
10. Respond with ONLY a JSON object of this exact shape, no other text:
{"status": "supported_by_evidence" or "insufficient_evidence", "answer": "...", "key_points": [{"text": "...", "evidence_refs": [1,2]}], "next_steps": [{"text": "...", "evidence_refs": [1]}], "asserts_mandatory": true or false, "asserts_certification_claim": true or false, "asserts_safety_claim": true or false, "asserts_legality_claim": true or false}
"""


def _build_evidence_block(chunks):
    lines = []
    for i, c in enumerate(chunks, start=1):
        lines.append(
            f"[{i}] Standard: {c['standard_number']} | Section: {c['section']} | "
            f"Page: {c['page_number']}\n{c['chunk_text']}"
        )
    return "\n\n".join(lines)


def _build_citations(chunks):
    """Built directly from retrieved chunks only — never from Gemini's
    output — same convention as hallmarking_service._build_citations."""
    seen = set()
    citations = []
    for c in chunks:
        key = (c["standard_number"], c["section"], c["page_number"])
        if key in seen:
            continue
        seen.add(key)
        citations.append({
            "source_reference": (
                f"{c['standard_number']}, {c['section']}" if c["standard_number"] and c["section"]
                else c["standard_number"] or c["section"] or c["document_title"]
            ),
            "source_url": c["source_url"],
        })
    return citations


def _evidence_text_has_keyword(chunks, keywords):
    combined = " ".join(c["chunk_text"] for c in chunks).lower()
    return any(re.search(re.escape(kw), combined) for kw in keywords)


def _text_has_keyword(text: str, keywords) -> bool:
    lowered = text.lower()
    return any(re.search(re.escape(kw), lowered) for kw in keywords)


def _valid_standard_numbers(chunks):
    return {c["standard_number"] for c in chunks if c["standard_number"]}


def _output_mentions_hallucinated_standard(all_text: str, valid_standards) -> bool:
    """SAFETY NET 2: any 'IS <number>'-shaped token in Gemini's text that
    doesn't match a standard_number actually retrieved is treated as a
    hallucinated standard."""
    mentioned = {m.group(0).upper().replace("-", " ").strip() for m in IS_NUMBER_PATTERN.finditer(all_text)}
    if not mentioned:
        return False
    normalized_valid = {str(s).upper().replace("-", " ").strip() for s in valid_standards}
    return any(m not in normalized_valid for m in mentioned)


def _filter_refs(items, max_index):
    """SAFETY NET 1: drops any evidence_refs Gemini invented that don't
    correspond to an actually-retrieved evidence number, and drops the whole
    item if none of its refs were real (i.e. it wasn't actually grounded).
    Applied to both key_points and next_steps, which doubles as the
    'action validation' guard from the spec (next_steps must be
    evidence-backed, same mechanism as key_points)."""
    cleaned = []
    for item in items:
        text = item.get("text", "").strip()
        if not text:
            continue
        refs = [r for r in item.get("evidence_refs", []) if isinstance(r, int) and 1 <= r <= max_index]
        if not refs:
            continue
        cleaned.append(text)
    return cleaned


def _insufficient_response(question: str):
    return {
        "question": question,
        "answer": INSUFFICIENT_EVIDENCE_MSG,
        "key_points": [],
        "next_steps": [],
        "status": STATUS_INSUFFICIENT,
        "citations": [],
        "limitations": [INSUFFICIENT_EVIDENCE_LIMITATION],
    }


def get_consumer_help(db: Session, question: str):
    """
    Returns a dict matching the M14 response shape:
      question, answer, key_points, next_steps, status, citations, limitations
    Raises on embedding/database/Gemini failure — caller (route) handles it,
    same convention as get_hallmarking_help / get_rag_response.
    """
    chunks = search_chunks(db, question, top_k=TOP_K)

    if not chunks:
        return _insufficient_response(question)

    valid_standards = _valid_standard_numbers(chunks)
    evidence_block = _build_evidence_block(chunks)
    user_message = f"QUESTION: {question}\n\nEVIDENCE EXCERPTS:\n{evidence_block}"

    response = client.models.generate_content(
        model=MODEL_NAME,
        contents=user_message,
        config=genai_types.GenerateContentConfig(
            system_instruction=SYSTEM_PROMPT,
            max_output_tokens=8000,
            response_mime_type="application/json",
            temperature=0.1,
        ),
    )

    try:
        parsed = json.loads(response.text)
    except (json.JSONDecodeError, AttributeError, TypeError):
        return _insufficient_response(question)
    if not isinstance(parsed, dict):
        return _insufficient_response(question)

    if parsed.get("status") == STATUS_INSUFFICIENT:
        return _insufficient_response(question)

    answer = (parsed.get("answer") or "").strip()
    if not answer:
        return _insufficient_response(question)

    raw_key_points = parsed.get("key_points", [])
    raw_next_steps = parsed.get("next_steps", [])
    if not isinstance(raw_key_points, list):
        raw_key_points = []
    if not isinstance(raw_next_steps, list):
        raw_next_steps = []

    # SAFETY NET 1 / ACTION VALIDATION: strip any key point / next step
    # whose evidence_refs don't correspond to actually-retrieved evidence.
    key_points = _filter_refs(raw_key_points, len(chunks))
    next_steps = _filter_refs(raw_next_steps, len(chunks))

    combined_output_text = " ".join([answer] + key_points + next_steps)

    # SAFETY NET 2: reject a hallucinated standard number anywhere in the text.
    if _output_mentions_hallucinated_standard(combined_output_text, valid_standards):
        return _insufficient_response(question)
    # SAFETY NET 3 & 4: mandatory/legal, certification, safety, and legality
    # claims are never taken on Gemini's word alone. For each category, if
    # the output asserts a claim in that category (via its own flag or by
    # using matching language in the text) but the RAW retrieved evidence
    # text does not contain matching language, reject the whole response.
    assertion_flags = {
        "mandatory": bool(parsed.get("asserts_mandatory")),
        "certification": bool(parsed.get("asserts_certification_claim")),
        "safety": bool(parsed.get("asserts_safety_claim")),
        "legality": bool(parsed.get("asserts_legality_claim")),
    }
    for category, keywords in CLAIM_CATEGORIES.items():
        output_claims_it = assertion_flags[category] or _text_has_keyword(combined_output_text, keywords)
        if output_claims_it and not _evidence_text_has_keyword(chunks, keywords):
            return _insufficient_response(question)
    return {
        "question": question,
        "answer": answer,
        "key_points": key_points,
        "next_steps": next_steps,
        "status": STATUS_SUPPORTED,
        "citations": _build_citations(chunks),
        "limitations": [],
    }