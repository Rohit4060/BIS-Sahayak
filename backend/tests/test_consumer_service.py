import json

import pytest

from services import consumer_service


def _chunk(
    standard_number="IS 1417",
    section="Jeweller Guidelines",
    page_number=1,
    chunk_text="The registered jeweller must follow the applicable requirements.",
    source_url="https://example.test/source.pdf",
    document_title="Test BIS Document",
):
    return {
        "standard_number": standard_number,
        "section": section,
        "page_number": page_number,
        "chunk_text": chunk_text,
        "source_url": source_url,
        "document_title": document_title,
    }


def _gemini_response(payload):
    class Response:
        text = json.dumps(payload)

    return Response()


def _patch_gemini(monkeypatch, payload):
    calls = []

    def generate_content(**kwargs):
        calls.append(kwargs)
        return _gemini_response(payload)

    monkeypatch.setattr(
        consumer_service.client.models,
        "generate_content",
        generate_content,
    )
    return calls


def _supported_payload(
    answer="The evidence supports this answer.",
    key_points=None,
    next_steps=None,
    **flags,
):
    return {
        "status": consumer_service.STATUS_SUPPORTED,
        "answer": answer,
        "key_points": key_points or [
            {"text": "Grounded point.", "evidence_refs": [1]}
        ],
        "next_steps": next_steps or [
            {"text": "Grounded next step.", "evidence_refs": [1]}
        ],
        "asserts_mandatory": flags.get("asserts_mandatory", False),
        "asserts_certification_claim": flags.get(
            "asserts_certification_claim", False
        ),
        "asserts_safety_claim": flags.get("asserts_safety_claim", False),
        "asserts_legality_claim": flags.get("asserts_legality_claim", False),
    }


def test_no_chunks_returns_insufficient_evidence(monkeypatch):
    monkeypatch.setattr(consumer_service, "search_chunks", lambda db, q, top_k: [])

    result = consumer_service.get_consumer_help(object(), "Any BIS question")

    assert result["status"] == consumer_service.STATUS_INSUFFICIENT
    assert result["answer"] == consumer_service.INSUFFICIENT_EVIDENCE_MSG
    assert result["key_points"] == []
    assert result["next_steps"] == []
    assert result["citations"] == []


def test_invalid_gemini_json_returns_insufficient_evidence(monkeypatch):
    chunks = [_chunk()]
    monkeypatch.setattr(
        consumer_service, "search_chunks", lambda db, q, top_k: chunks
    )

    class Response:
        text = "{not valid json"

    monkeypatch.setattr(
        consumer_service.client.models,
        "generate_content",
        lambda **kwargs: Response(),
    )

    result = consumer_service.get_consumer_help(object(), "Any BIS question")

    assert result["status"] == consumer_service.STATUS_INSUFFICIENT
    assert result["answer"] == consumer_service.INSUFFICIENT_EVIDENCE_MSG


def test_non_dict_gemini_json_returns_insufficient_evidence(monkeypatch):
    chunks = [_chunk()]
    monkeypatch.setattr(
        consumer_service, "search_chunks", lambda db, q, top_k: chunks
    )
    _patch_gemini(monkeypatch, ["not", "an", "object"])

    result = consumer_service.get_consumer_help(object(), "Any BIS question")

    assert result["status"] == consumer_service.STATUS_INSUFFICIENT
    assert result["citations"] == []


def test_gemini_can_explicitly_report_insufficient_evidence(monkeypatch):
    chunks = [_chunk()]
    monkeypatch.setattr(
        consumer_service, "search_chunks", lambda db, q, top_k: chunks
    )
    _patch_gemini(
        monkeypatch,
        {
            "status": consumer_service.STATUS_INSUFFICIENT,
            "answer": consumer_service.INSUFFICIENT_EVIDENCE_MSG,
            "key_points": [],
            "next_steps": [],
        },
    )

    result = consumer_service.get_consumer_help(object(), "Question")

    assert result["status"] == consumer_service.STATUS_INSUFFICIENT
    assert result["answer"] == consumer_service.INSUFFICIENT_EVIDENCE_MSG
    assert result["limitations"] == [consumer_service.INSUFFICIENT_EVIDENCE_LIMITATION]


def test_empty_answer_returns_insufficient_evidence(monkeypatch):
    chunks = [_chunk()]
    monkeypatch.setattr(
        consumer_service, "search_chunks", lambda db, q, top_k: chunks
    )
    _patch_gemini(
        monkeypatch,
        _supported_payload(
            answer="   ",
            key_points=[],
            next_steps=[],
        ),
    )

    result = consumer_service.get_consumer_help(object(), "Question")

    assert result["status"] == consumer_service.STATUS_INSUFFICIENT
    assert result["answer"] == consumer_service.INSUFFICIENT_EVIDENCE_MSG


def test_invalid_evidence_refs_are_filtered_out(monkeypatch):
    chunks = [_chunk()]
    monkeypatch.setattr(
        consumer_service, "search_chunks", lambda db, q, top_k: chunks
    )
    _patch_gemini(
        monkeypatch,
        _supported_payload(
            key_points=[
                {"text": "Real point.", "evidence_refs": [1]},
                {"text": "Invented point.", "evidence_refs": [99]},
                {"text": "Unreferenced point.", "evidence_refs": []},
            ],
            next_steps=[
                {"text": "Real step.", "evidence_refs": [1]},
                {"text": "Invented step.", "evidence_refs": [2]},
            ],
        ),
    )

    result = consumer_service.get_consumer_help(object(), "Question")

    assert result["status"] == consumer_service.STATUS_SUPPORTED
    assert result["key_points"] == ["Real point."]
    assert result["next_steps"] == ["Real step."]


def test_hallucinated_standard_number_rejects_response(monkeypatch):
    chunks = [
        _chunk(
            standard_number="IS 1417",
            chunk_text="The evidence refers to IS 1417."
        )
    ]
    monkeypatch.setattr(
        consumer_service, "search_chunks", lambda db, q, top_k: chunks
    )
    _patch_gemini(
        monkeypatch,
        _supported_payload(
            answer="The product must comply with IS 12345.",
        ),
    )

    result = consumer_service.get_consumer_help(object(), "Question")

    assert result["status"] == consumer_service.STATUS_INSUFFICIENT
    assert result["answer"] == consumer_service.INSUFFICIENT_EVIDENCE_MSG
    assert result["citations"] == []


def test_mandatory_claim_without_matching_evidence_is_rejected(monkeypatch):
    chunks = [
        _chunk(
            chunk_text="The document recommends following the relevant guidance."
        )
    ]
    monkeypatch.setattr(
        consumer_service, "search_chunks", lambda db, q, top_k: chunks
    )
    _patch_gemini(
        monkeypatch,
        _supported_payload(
            answer="This requirement is mandatory.",
            asserts_mandatory=True,
        ),
    )

    result = consumer_service.get_consumer_help(object(), "Question")

    assert result["status"] == consumer_service.STATUS_INSUFFICIENT
    assert result["answer"] == consumer_service.INSUFFICIENT_EVIDENCE_MSG


def test_certification_safety_and_legality_claims_require_raw_evidence(monkeypatch):
    chunks = [
        _chunk(
            chunk_text=(
                "The evidence describes the product and its applicable "
                "requirements, but does not make a certification, safety, "
                "or legality claim."
            )
        )
    ]
    monkeypatch.setattr(
        consumer_service, "search_chunks", lambda db, q, top_k: chunks
    )
    _patch_gemini(
        monkeypatch,
        _supported_payload(
            answer="The product is BIS certified, safe to use, and legal.",
            asserts_certification_claim=True,
            asserts_safety_claim=True,
            asserts_legality_claim=True,
        ),
    )

    result = consumer_service.get_consumer_help(object(), "Question")

    assert result["status"] == consumer_service.STATUS_INSUFFICIENT
    assert result["answer"] == consumer_service.INSUFFICIENT_EVIDENCE_MSG


def test_fully_supported_response_preserves_grounded_answer_and_citations(monkeypatch):
    chunks = [
        _chunk(
            standard_number="BIS Hallmarking Regulations 2018",
            section="Jeweller Guidelines",
            page_number=10,
            chunk_text=(
                "All test reports indicating failure are communicated to the "
                "registered jeweller within 7 days."
            ),
            source_url="https://www.bis.gov.in/jeweller-guidelines.pdf",
            document_title="BIS Hallmarking Regulations 2018",
        )
    ]
    monkeypatch.setattr(
        consumer_service, "search_chunks", lambda db, q, top_k: chunks
    )

    answer = "All test reports indicating failure are communicated within 7 days."
    payload = _supported_payload(
        answer=answer,
        key_points=[
            {"text": "Failure reports are communicated within 7 days.", "evidence_refs": [1]}
        ],
        next_steps=[
            {"text": "Review the cited jeweller guidelines.", "evidence_refs": [1]}
        ],
    )
    calls = _patch_gemini(monkeypatch, payload)

    result = consumer_service.get_consumer_help(
        object(),
        "What happens if a hallmarked gold article fails testing?",
    )

    assert result["status"] == consumer_service.STATUS_SUPPORTED
    assert result["answer"] == answer
    assert result["key_points"] == [
        "Failure reports are communicated within 7 days."
    ]
    assert result["next_steps"] == [
        "Review the cited jeweller guidelines."
    ]
    assert result["citations"]
    assert result["citations"][0]["source_url"] == (
        "https://www.bis.gov.in/jeweller-guidelines.pdf"
    )
    assert result["citations"][0]["source_reference"] == (
        "BIS Hallmarking Regulations 2018, Jeweller Guidelines"
    )
    assert calls
    assert calls[0]["config"].max_output_tokens == 8000
