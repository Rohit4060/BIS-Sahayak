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
import re

from google import genai
from google.genai import types as genai_types
from sqlalchemy.orm import Session

from services.search_service import search_chunks

MODEL_NAME = "gemini-2.5-flash"
TOP_K = 5
INSUFFICIENT_EVIDENCE_MSG = "I could not verify this from the available BIS sources."

# These are deliberately a closed set: the API must not silently pass an
# arbitrary instruction to the model.  The request model in main.py enforces
# the same list for explicit user choices.
SUPPORTED_LANGUAGES = {
    "en": "English",
    "hi": "Hindi",
    "bn": "Bengali",
    "mr": "Marathi",
    "ta": "Tamil",
    "te": "Telugu",
    "kn": "Kannada",
    "ml": "Malayalam",
    "gu": "Gujarati",
    "pa": "Punjabi",
}

# Fallbacks are application-controlled, so an insufficient-evidence response
# stays safe even when Gemini replies in English.  They intentionally express
# only the existing fail-safe meaning and introduce no BIS facts.
INSUFFICIENT_EVIDENCE_MESSAGES = {
    "en": INSUFFICIENT_EVIDENCE_MSG,
    "hi": "मैं उपलब्ध BIS स्रोतों से इसकी पुष्टि नहीं कर सका।",
    "bn": "উপলব্ধ BIS উৎস থেকে আমি এটি যাচাই করতে পারিনি।",
    "mr": "उपलब्ध BIS स्रोतांमधून मी याची पडताळणी करू शकलो नाही.",
    "ta": "கிடைக்கக்கூடிய BIS ஆதாரங்களிலிருந்து இதை என்னால் சரிபார்க்க முடியவில்லை.",
    "te": "అందుబాటులో ఉన్న BIS మూలాల నుండి నేను దీన్ని ధృవీకరించలేకపోయాను.",
    "kn": "ಲಭ್ಯವಿರುವ BIS ಮೂಲಗಳಿಂದ ಇದನ್ನು ನಾನು ಪರಿಶೀಲಿಸಲು ಸಾಧ್ಯವಾಗಲಿಲ್ಲ.",
    "ml": "ലഭ്യമായ BIS സ്രോതസ്സുകളിൽ നിന്ന് ഇത് സ്ഥിരീകരിക്കാൻ എനിക്ക് കഴിഞ്ഞില്ല.",
    "gu": "ઉપલબ્ધ BIS સ્રોતોમાંથી હું આ ચકાસી શક્યો નથી.",
    "pa": "ਮੈਂ ਉਪਲਬਧ BIS ਸਰੋਤਾਂ ਤੋਂ ਇਸਦੀ ਪੁਸ਼ਟੀ ਨਹੀਂ ਕਰ ਸਕਿਆ।",
}

# Script detection is only a default when no controlled language code is
# supplied. Devanagari is shared by Hindi and Marathi, so it defaults to
# Hindi; Marathi users can request "mr" explicitly.
SCRIPT_LANGUAGE_RANGES = (
    ("hi", "\u0900", "\u097f"),
    ("bn", "\u0980", "\u09ff"),
    ("gu", "\u0a80", "\u0aff"),
    ("pa", "\u0a00", "\u0a7f"),
    ("ta", "\u0b80", "\u0bff"),
    ("te", "\u0c00", "\u0c7f"),
    ("kn", "\u0c80", "\u0cff"),
    ("ml", "\u0d00", "\u0d7f"),
)

# This guards the most common BIS identifier form in model prose. Citations
# themselves never come from model output; they are constructed below from
# retrieved chunk rows.
IS_NUMBER_PATTERN = re.compile(r"\bIS[\s-]?\d{2,6}\b", re.IGNORECASE)

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
   respond with the exact insufficient-evidence message supplied with the
   request.
   You may briefly note what the available evidence does cover, if anything, but
   you must not fill the gap with general knowledge.
5. Clearly distinguish between what the evidence explicitly states and anything
   that is ambiguous or only partially covered.
6. Write the answer in the requested response language. Keep every BIS/IS
   identifier, standard number, clause number, section number, technical code,
   document identifier, and evidence marker exactly as it appears in the
   supplied evidence. Do not translate, transliterate, reformat, or invent any
   of them.

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


def detect_language(question: str) -> str:
    """Return the supported language implied by a Unicode script, or English.

    Retrieval remains the existing Gemini embedding + pgvector path. This
    function merely chooses the response-language instruction; it never
    translates or rewrites a user's query or retrieved BIS evidence.
    """
    for language, start, end in SCRIPT_LANGUAGE_RANGES:
        if any(start <= character <= end for character in question):
            return language
    return "en"


def resolve_language(question: str, language: str | None = None) -> str:
    return language if language in SUPPORTED_LANGUAGES else detect_language(question)


def insufficient_evidence_message(language: str) -> str:
    return INSUFFICIENT_EVIDENCE_MESSAGES[language]


def _language_instruction(language: str) -> str:
    """A request-specific, non-negotiable output-language rule for Gemini."""
    message = insufficient_evidence_message(language)
    return (
        f"FINAL RESPONSE LANGUAGE: {SUPPORTED_LANGUAGES[language]} ({language}). "
        "This is mandatory: write all normal explanatory prose in that language. "
        "Do not answer in English unless the requested language is English. "
        "Keep BIS/IS identifiers, standard numbers, clause/section numbers, "
        "technical codes, document identifiers, and [evidence markers] exactly "
        "as supplied. If the evidence is insufficient, respond with exactly: "
        f'"{message}"'
    )


def _answer_uses_requested_script(answer: str, language: str) -> bool:
    """Reject an English model reply for an explicitly non-English response.

    This only validates the response language; it does not translate, alter,
    or otherwise process the answer or retrieved evidence.
    """
    if language == "en":
        return True
    for code, start, end in SCRIPT_LANGUAGE_RANGES:
        if code == language or (language == "mr" and code == "hi"):
            return any(start <= character <= end for character in answer)
    return False


def _output_mentions_hallucinated_standard(answer: str, chunks) -> bool:
    mentioned = {
        match.group(0).upper().replace("-", " ").strip()
        for match in IS_NUMBER_PATTERN.finditer(answer)
    }
    valid = {
        str(chunk["standard_number"]).upper().replace("-", " ").strip()
        for chunk in chunks if chunk.get("standard_number")
    }
    # A full document identifier can contain a part/year suffix while prose
    # legitimately refers to its stable "IS 302" stem. Accept that exact stem
    # only when it was derived from a retrieved identifier.
    valid_stems = {
        match.group(0).upper().replace("-", " ").strip()
        for identifier in valid.copy()
        for match in IS_NUMBER_PATTERN.finditer(identifier)
    }
    valid.update(valid_stems)
    return any(standard not in valid for standard in mentioned)


def get_rag_response(db: Session, question: str, language: str | None = None):
    """
    Returns {"answer": str, "citations": list[dict]}.
    Raises on embedding/database/Gemini failure — caller handles it.
    """
    response_language = resolve_language(question, language)
    chunks = search_chunks(db, question, top_k=TOP_K)

    if not chunks:
        return {"answer": insufficient_evidence_message(response_language), "citations": []}

    evidence_block = _build_evidence_block(chunks)
    user_message = f"QUESTION: {question}\n\nEVIDENCE EXCERPTS:\n{evidence_block}"

    response = client.models.generate_content(
        model=MODEL_NAME,
        contents=user_message,
        config=genai_types.GenerateContentConfig(
            system_instruction=f"{SYSTEM_PROMPT}\n\n{_language_instruction(response_language)}",
            max_output_tokens=1000,
        ),
    )

    answer = (response.text or "").strip()
    if (
        not answer
        or not _answer_uses_requested_script(answer, response_language)
        or _output_mentions_hallucinated_standard(answer, chunks)
    ):
        return {"answer": insufficient_evidence_message(response_language), "citations": []}

    # A model may use either the English or requested localized insufficient
    # wording. In either case, return the controlled fallback without sources.
    if answer in INSUFFICIENT_EVIDENCE_MESSAGES.values():
        return {"answer": insufficient_evidence_message(response_language), "citations": []}
    return {"answer": answer, "citations": _build_citations(chunks)}
