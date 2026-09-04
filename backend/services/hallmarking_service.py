"""
Consumer Hallmarking Assistant for /api/hallmarking/help.

Flow:
  consumer question
    -> embed + pgvector retrieval (reuses search_service, identical to
       rag_service.py — no duplicated embedding/search logic)
    -> Gemini answers ONLY from the retrieved evidence and must self-report
       whether its answer asserts a mandatory/legal requirement, and which
       evidence numbers each key point / next step is grounded in
    -> SAFETY NET 1: any evidence index Gemini references that wasn't
       actually retrieved is discarded in code — bad indices never produce
       an unsupported citation
    -> SAFETY NET 2: any IS/standard number mentioned anywhere in Gemini's
       text output that doesn't match an actually-retrieved standard_number
       is treated as a hallucinated standard and rejects the response
    -> SAFETY NET 3: mirrors compliance_service.py's mandatory-claim guard —
       "mandatory"/"compulsory"/etc. language is never taken on Gemini's
       word alone. If Gemini's answer asserts a mandatory/legal requirement
       (either via its own "asserts_mandatory" flag or by using mandatory
       language in the text) but the RAW retrieved evidence text itself does
       not contain explicit mandatory language, the response is rejected and
       downgraded to insufficient_evidence rather than shown to the user.
    -> citations are built directly from retrieved chunk rows, never from
       Gemini's own text (same convention as rag_service/standards_recommender)
    -> if no evidence, or the response fails a safety net, return the honest
       "could not verify" message, never a guess

This module deliberately does NOT hard-code any hallmarking symbols, purity
marks, HUID details, or legal rules from general knowledge. All such
specifics must come from retrieved evidence, or the assistant refuses.
"""
import json
import os
import re

from google import genai
from google.genai import types as genai_types
from sqlalchemy.orm import Session

from services.search_service import search_chunks

MODEL_NAME = "gemini-2.5-flash"
TOP_K = 8  # narrower than standards_recommender/compliance (single consumer
           # answer, not a multi-standard survey), wider than /api/chat's 5
           # since hallmarking questions often span symbols + process + redressal

INSUFFICIENT_EVIDENCE_MSG = "I could not verify this from the available BIS sources."

STATUS_SUPPORTED = "supported_by_evidence"
STATUS_INSUFFICIENT = "insufficient_evidence"

# Same keyword list/convention as compliance_service.py's MANDATORY_KEYWORDS,
# used here in both directions: to detect if Gemini's OUTPUT asserts a
# mandatory/legal claim, and to check if the retrieved EVIDENCE actually
# supports one.
MANDATORY_KEYWORDS = [
    "mandatory",
    "compulsory",
    "compulsorily",
    "shall be certified",
    "shall obtain",
    "shall comply",
    "required to obtain",
    "legally required",
    "legally binding",
    "not eligible",
    "ineligible",
    "shall not",
    "prohibited",
    "liable to cancellation",
    "liable for",
    "shall be liable",
]

# Matches things like "IS 1417", "IS-1417", "IS1417:2016" so we can catch a
# standard number Gemini mentions in prose that wasn't actually retrieved.
IS_NUMBER_PATTERN = re.compile(r"\bIS[\s-]?\d{2,6}\b", re.IGNORECASE)

client = genai.Client(api_key=os.environ.get("GEMINI_API_KEY"))

SYSTEM_PROMPT = """You are BIS Sahayak AI, helping consumers understand
hallmarking-related questions using ONLY retrieved evidence excerpts from
official BIS documents. This is a consumer education tool, not a general
jewellery chatbot — stay strictly within what the evidence supports.

You must follow these rules strictly:

1. Answer using ONLY the supplied numbered EVIDENCE excerpts. Do not use
   outside or general knowledge, even if you believe you know the answer.
2. NEVER invent or assume: hallmarking rules, BIS standards or their numbers,
   clauses, hallmark symbols/codes, purity marks, HUID details, legal
   requirements, certification requirements, testing procedures, or
   complaint/redressal procedures. If it is not explicitly in the evidence,
   do not state it.
3. Only mention a standard number (e.g. "IS 1417") if it appears verbatim in
   the evidence excerpts you were given. Never write a standard number from
   memory.
4. Every key point and next step must be traceable to specific evidence
   excerpt numbers, referenced as "evidence_refs": [1, 2] (the numbers
   correspond to the [N] markers in the evidence block).
5. Distinguish carefully between the evidence saying something is
   "applicable", "recommended", or "may apply" versus explicitly stating it
   is "mandatory" or a "legal requirement". Do NOT upgrade the former into
   the latter.
6. Set "asserts_mandatory": true ONLY if the evidence excerpts themselves
   explicitly use mandatory/legal-requirement language for what you are
   telling the user. Otherwise false. Default to false when uncertain.
7. If the evidence does not contain enough information to answer the
   question, set "status" to "insufficient_evidence", set "answer" to
   exactly "I could not verify this from the available BIS sources.", and
   leave "key_points" and "next_steps" empty. Do not fill the gap with
   general knowledge.
8. Use simple, consumer-friendly language — avoid unexplained jargon.
9. Respond with ONLY a JSON object of this exact shape, no other text:
{"status": "supported_by_evidence" or "insufficient_evidence", "answer": "...", "key_points": [{"text": "...", "evidence_refs": [1,2]}], "next_steps": [{"text": "...", "evidence_refs": [1]}], "asserts_mandatory": true or false}
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
    output — same convention as rag_service._build_citations."""
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


def _evidence_text_has_mandatory_language(chunks):
    """Same safety-net convention as compliance_service.py: checks the ACTUAL
    retrieved evidence text for explicit mandatory-language keywords,
    independent of what Gemini claims."""
    combined = " ".join(c["chunk_text"] for c in chunks).lower()
    return any(re.search(re.escape(kw), combined) for kw in MANDATORY_KEYWORDS)


def _text_asserts_mandatory(text: str) -> bool:
    lowered = text.lower()
    return any(re.search(re.escape(kw), lowered) for kw in MANDATORY_KEYWORDS)


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
    item if none of its refs were real (i.e. it wasn't actually grounded)."""
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
        "limitations": [],
    }


def get_hallmarking_help(db: Session, question: str):
    """
    Returns a dict matching the M13 response shape:
      question, answer, key_points, next_steps, status, citations, limitations
    Raises on embedding/database/Gemini failure — caller (route) handles it,
    same convention as get_rag_response / recommend_standards.
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
            max_output_tokens=1500,
            response_mime_type="application/json",
            temperature=0.1,
        ),
    )
    try:
        parsed = json.loads(response.text)
    except (json.JSONDecodeError, AttributeError, TypeError):
        return _insufficient_response(question)

    if parsed.get("status") == STATUS_INSUFFICIENT:
        return _insufficient_response(question)

    answer = (parsed.get("answer") or "").strip()
    if not answer:
        return _insufficient_response(question)

    raw_key_points = parsed.get("key_points", [])
    raw_next_steps = parsed.get("next_steps", [])

    # SAFETY NET 1: strip any key point / next step whose evidence_refs don't
    # correspond to actually-retrieved evidence.
    key_points = _filter_refs(raw_key_points, len(chunks))
    next_steps = _filter_refs(raw_next_steps, len(chunks))

    combined_output_text = " ".join([answer] + key_points + next_steps)

    # SAFETY NET 2: reject a hallucinated standard number anywhere in the text.
    if _output_mentions_hallucinated_standard(combined_output_text, valid_standards):
        return _insufficient_response(question)

    # SAFETY NET 3: mandatory/legal claims are never taken on Gemini's word
    # alone — same convention as compliance_service.py's confirmed_mandatory
    # safety net, applied here as an outright rejection since this endpoint
    # gives one consumer-facing answer rather than a per-requirement status.
    output_claims_mandatory = bool(parsed.get("asserts_mandatory")) or _text_asserts_mandatory(combined_output_text)
    if output_claims_mandatory and not _evidence_text_has_mandatory_language(chunks):
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
