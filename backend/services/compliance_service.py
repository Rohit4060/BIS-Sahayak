"""
Product -> Certification & Compliance Intelligence for /api/compliance/check.

Flow:
  product description
    -> embed + pgvector retrieval (reuses search_service, identical to
       standards_recommender.py — no duplicated embedding/search logic)
    -> group retrieved chunks by standard (reuses standards_recommender's
       grouping/citation helpers — no duplicated grouping logic)
    -> Gemini evaluates ONLY the retrieved evidence and extracts concrete
       compliance/testing requirements per candidate standard, assigning a
       status per requirement
    -> SAFETY NET 1: any standard_number in Gemini's output that doesn't match
       an actually-retrieved candidate is discarded in code
    -> SAFETY NET 2: "confirmed_mandatory" is never taken on Gemini's word
       alone — code re-checks the evidence text for explicit mandatory-
       language keywords before allowing that status to stand
    -> citations are built directly from retrieved chunk rows, never from
       Gemini's own text
    -> if no candidate clears evaluation, return the honest
       "could not verify" message, never a guess
"""
import json
import os
import re

from google import genai
from google.genai import types as genai_types
from sqlalchemy.orm import Session

from services.search_service import search_chunks
from services.standards_recommender import (
    _group_chunks_by_standard,
    _build_citations_for_group,
    _build_evidence_list_for_group,
)

MODEL_NAME = "gemini-2.5-flash"
TOP_K = 20  # same as standards_recommender — need coverage across standards

INSUFFICIENT_EVIDENCE_MSG = (
    "I could not verify the required compliance steps from the available BIS sources."
)

VALID_STATUSES = {
    "potentially_applicable",
    "supported_by_evidence",
    "confirmed_mandatory",
    "insufficient_evidence",
}

# Keywords the evidence text must contain for a "confirmed_mandatory" status
# to survive the safety-net check. Case-insensitive.
MANDATORY_KEYWORDS = [
    "mandatory",
    "compulsory",
    "compulsorily",
    "shall be certified",
    "shall obtain",
    "shall comply",
    "required to obtain",
]

client = genai.Client(api_key=os.environ.get("GEMINI_API_KEY"))

SYSTEM_PROMPT = """You are BIS Sahayak AI, extracting certification and
compliance requirements for a product, using ONLY retrieved evidence excerpts
grouped by candidate standard.

You must follow these rules strictly:

1. You will be given a PRODUCT DESCRIPTION, a list of CANDIDATE STANDARDS with
   numbered evidence excerpts under each, and a "valid candidate identifiers"
   list. You may ONLY reference standard_number values that appear EXACTLY in
   that valid identifiers list. Never output a standard_number that is not in
   that list, and never invent a new one.
2. For each candidate standard with genuine relevance, extract one or more
   concrete REQUIREMENTS the evidence actually describes (e.g. a specific
   certification scheme, a testing obligation, a marking requirement). Do not
   invent requirements the evidence does not state.
3. For each requirement, output:
   - "requirement": a concise statement of what the evidence says, grounded
     in the text, referencing evidence numbers like [1], [2]
   - "status": one of exactly these four values:
     "potentially_applicable" (standard seems relevant but evidence doesn't
       clearly confirm a specific obligation),
     "supported_by_evidence" (evidence describes this requirement but doesn't
       explicitly call it a mandatory legal obligation),
     "confirmed_mandatory" (evidence EXPLICITLY states this is a mandatory /
       compulsory legal requirement — use this ONLY when the evidence text
       itself uses clearly mandatory language),
     "insufficient_evidence" (relevant standard, but evidence is too thin to
       state a specific requirement)
   - "reason": brief grounded explanation
   - "testing_requirement": a specific testing obligation IF AND ONLY IF the
     evidence explicitly describes one, otherwise null
   - "next_step": one concrete, actionable next step for the manufacturer,
     grounded in the evidence (e.g. "Apply for BIS license under scheme X"),
     or null if the evidence doesn't support a concrete next step
4. Never claim "confirmed_mandatory" unless the evidence text explicitly uses
   mandatory/compulsory language. When in doubt, use "supported_by_evidence"
   or "potentially_applicable" instead.
5. If a candidate standard's evidence is not actually relevant, OMIT it
   entirely.
6. If NONE of the candidate standards are genuinely relevant, output an empty
   "standards" list. Do not force a match.
7. Respond with ONLY a JSON object of this exact shape, no other text:
{"standards": [{"standard_number": "...", "requirements": [{"requirement": "...", "status": "...", "reason": "...", "testing_requirement": "..." or null, "next_step": "..." or null}]}]}
"""


def _evidence_text_has_mandatory_language(chunks):
    """Safety net for 'confirmed_mandatory': re-checks the ACTUAL retrieved
    evidence text for explicit mandatory-language keywords, independent of
    what Gemini claims. Case-insensitive substring check."""
    combined = " ".join(c["chunk_text"] for c in chunks).lower()
    return any(re.search(re.escape(kw), combined) for kw in MANDATORY_KEYWORDS)


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


def check_compliance(db: Session, product_description: str):
    """
    Returns a dict:
      {
        "product_description": str,
        "standards": list[dict],   # each: standard_number, title, requirements, citations
        "limitations": str,
        "message": str | None,     # set when standards is empty
      }
    Raises on embedding/database/Gemini failure — caller (route) handles it,
    same convention as recommend_standards / get_rag_response.
    """
    limitations = (
        "This analysis is based only on the BIS documents currently indexed "
        "in this system. It is not a substitute for official BIS certification "
        "guidance, and mandatory-requirement determinations should be confirmed "
        "with BIS directly before making compliance decisions."
    )

    chunks = search_chunks(db, product_description, top_k=TOP_K)

    if not chunks:
        return {
            "product_description": product_description,
            "standards": [],
            "limitations": limitations,
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
            max_output_tokens=8000,
            response_mime_type="application/json",
            temperature=0.1,
        ),
    )

    try:
        parsed = json.loads(response.text)
        gemini_standards = parsed.get("standards", [])
    except (json.JSONDecodeError, AttributeError, TypeError):
        gemini_standards = []

    result_standards = []
    for std in gemini_standards:
        standard_key = std.get("standard_number")

        # SAFETY NET 1: enforced in code. A standard_number that wasn't
        # actually retrieved can never reach the user.
        if standard_key not in groups:
            continue

        group_chunks = groups[standard_key]
        mandatory_supported = _evidence_text_has_mandatory_language(group_chunks)

        requirements = []
        for req in std.get("requirements", []):
            status = req.get("status")
            if status not in VALID_STATUSES:
                status = "potentially_applicable"

            # SAFETY NET 2: "confirmed_mandatory" only survives if the actual
            # retrieved evidence text contains explicit mandatory language.
            if status == "confirmed_mandatory" and not mandatory_supported:
                status = "supported_by_evidence"

            requirements.append({
                "requirement": req.get("requirement", ""),
                "status": status,
                "reason": req.get("reason", ""),
                "testing_requirement": req.get("testing_requirement"),
                "next_step": req.get("next_step"),
            })

        if not requirements:
            continue

        result_standards.append({
            "standard_number": group_chunks[0]["standard_number"],
            "title": group_chunks[0]["document_title"],
            "requirements": requirements,
            "evidence": _build_evidence_list_for_group(group_chunks),
            "citations": _build_citations_for_group(group_chunks),
        })

    if not result_standards:
        return {
            "product_description": product_description,
            "standards": [],
            "limitations": limitations,
            "message": INSUFFICIENT_EVIDENCE_MSG,
        }

    return {
        "product_description": product_description,
        "standards": result_standards,
        "limitations": limitations,
    }