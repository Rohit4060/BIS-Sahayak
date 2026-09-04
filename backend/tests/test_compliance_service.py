"""
Automated tests for compliance_service.py — focused on the safety-net logic
that prevents hallucinated standards and unsupported mandatory claims from
reaching the user. These tests use mocked chunk data and a mocked Gemini
response; they do NOT call the real Gemini API or a real database.
"""
import pytest
from unittest.mock import patch, MagicMock

from services import compliance_service


def _fake_chunk(standard_number="IS 999 : 2024", section="1. TEST", page=1,
                 chunk_text="Manufacturers shall obtain mandatory certification."):
    return {
        "relevance_score": 0.9,
        "standard_number": standard_number,
        "document_title": "TEST STANDARD TITLE",
        "page_number": page,
        "section": section,
        "chunk_text": chunk_text,
        "source_url": "https://example.com/test-standard",
    }


class FakeGeminiResponse:
    """Mimics the shared generation helper's response value."""
    def __init__(self, text):
        self.text = text


def test_hallucinated_standard_is_discarded():
    """SAFETY NET 1: a standard_number Gemini invents, that was never actually
    retrieved, must never reach the response."""
    real_chunks = [_fake_chunk(standard_number="IS 999 : 2024")]

    gemini_json = (
        '{"standards": ['
        '{"standard_number": "IS 999 : 2024", "requirements": ['
        '{"requirement": "Real requirement", "status": "supported_by_evidence", '
        '"reason": "grounded", "testing_requirement": null, "next_step": null}'
        ']},'
        '{"standard_number": "IS 000 : FAKE", "requirements": ['
        '{"requirement": "Hallucinated requirement", "status": "confirmed_mandatory", '
        '"reason": "made up", "testing_requirement": null, "next_step": null}'
        ']}'
        ']}'
    )

    with patch.object(compliance_service, "search_chunks", return_value=real_chunks), \
         patch.object(compliance_service, "_generate_answer",
                      return_value=FakeGeminiResponse(gemini_json)):
        result = compliance_service.check_compliance(db=MagicMock(), product_description="test product")

    standard_numbers = [s["standard_number"] for s in result["standards"]]
    assert "IS 999 : 2024" in standard_numbers
    assert "IS 000 : FAKE" not in standard_numbers
    assert len(result["standards"]) == 1


def test_confirmed_mandatory_downgraded_without_keyword_support():
    """SAFETY NET 2: Gemini claiming 'confirmed_mandatory' is not enough — the
    actual retrieved evidence text must contain explicit mandatory language,
    or the status is downgraded to 'supported_by_evidence'."""
    # Evidence text deliberately has NO mandatory keywords.
    weak_chunks = [_fake_chunk(
        standard_number="IS 111 : 2024",
        chunk_text="This document provides general guidance for manufacturers.",
    )]

    gemini_json = (
        '{"standards": [{"standard_number": "IS 111 : 2024", "requirements": ['
        '{"requirement": "Some requirement", "status": "confirmed_mandatory", '
        '"reason": "claimed mandatory without support", "testing_requirement": null, "next_step": null}'
        ']}]}'
    )

    with patch.object(compliance_service, "search_chunks", return_value=weak_chunks), \
         patch.object(compliance_service, "_generate_answer",
                      return_value=FakeGeminiResponse(gemini_json)):
        result = compliance_service.check_compliance(db=MagicMock(), product_description="test product")

    assert result["standards"][0]["requirements"][0]["status"] == "supported_by_evidence"


def test_confirmed_mandatory_survives_with_keyword_support():
    """When the evidence text DOES contain explicit mandatory language,
    'confirmed_mandatory' should be allowed to stand."""
    strong_chunks = [_fake_chunk(
        standard_number="IS 222 : 2024",
        chunk_text="Certification under this scheme is mandatory for all manufacturers.",
    )]

    gemini_json = (
        '{"standards": [{"standard_number": "IS 222 : 2024", "requirements": ['
        '{"requirement": "Obtain certification", "status": "confirmed_mandatory", '
        '"reason": "evidence explicitly says mandatory", "testing_requirement": null, "next_step": null}'
        ']}]}'
    )

    with patch.object(compliance_service, "search_chunks", return_value=strong_chunks), \
         patch.object(compliance_service, "_generate_answer",
                      return_value=FakeGeminiResponse(gemini_json)):
        result = compliance_service.check_compliance(db=MagicMock(), product_description="test product")

    assert result["standards"][0]["requirements"][0]["status"] == "confirmed_mandatory"


def test_invalid_status_defaults_to_potentially_applicable():
    """If Gemini outputs a status value outside the allowed enum, it must be
    coerced to a safe default rather than passed through."""
    chunks = [_fake_chunk(standard_number="IS 333 : 2024")]

    gemini_json = (
        '{"standards": [{"standard_number": "IS 333 : 2024", "requirements": ['
        '{"requirement": "Some requirement", "status": "definitely_true_100_percent", '
        '"reason": "invalid status test", "testing_requirement": null, "next_step": null}'
        ']}]}'
    )

    with patch.object(compliance_service, "search_chunks", return_value=chunks), \
         patch.object(compliance_service, "_generate_answer",
                      return_value=FakeGeminiResponse(gemini_json)):
        result = compliance_service.check_compliance(db=MagicMock(), product_description="test product")

    assert result["standards"][0]["requirements"][0]["status"] == "potentially_applicable"


def test_no_retrieved_chunks_returns_insufficient_evidence():
    """If retrieval finds nothing at all, Gemini should never be called, and
    the response should be the honest insufficient-evidence message."""
    with patch.object(compliance_service, "search_chunks", return_value=[]), \
         patch.object(compliance_service, "_generate_answer") as mock_gemini:
        result = compliance_service.check_compliance(db=MagicMock(), product_description="test product")

    mock_gemini.assert_not_called()
    assert result["standards"] == []
    assert result["message"] == compliance_service.INSUFFICIENT_EVIDENCE_MSG


def test_malformed_gemini_json_returns_insufficient_evidence():
    """If Gemini's response isn't valid JSON, the service should fail safe
    (empty result + honest message), never crash or fabricate content."""
    chunks = [_fake_chunk()]

    with patch.object(compliance_service, "search_chunks", return_value=chunks), \
         patch.object(compliance_service, "_generate_answer",
                      return_value=FakeGeminiResponse("this is not valid json {{{")):
        result = compliance_service.check_compliance(db=MagicMock(), product_description="test product")

    assert result["standards"] == []
    assert result["message"] == compliance_service.INSUFFICIENT_EVIDENCE_MSG
