"""
Tests for M13 Hallmarking Assistant (services/hallmarking_service.py and
POST /api/hallmarking/help).

Convention: mock services.search_chunks (retrieval) and the Gemini
client.models.generate_content call directly, so these are fast, offline
unit tests that never touch a real DB or the live Gemini API. Positive-path
fixtures below are isolated test data, NOT inserted into any real database —
see M13 instructions section 11 (test data rule).

ADJUST the two import lines below to match this project's actual test
harness / TestClient setup if it differs (e.g. if there's an existing
conftest.py with a shared `client` or `db_session` fixture, use that instead
of the ad-hoc mocks here).
"""
import json
from unittest.mock import MagicMock, patch

import pytest

from services import hallmarking_service as hs


def _fake_chunk(standard_number="IS 1417", section="Cl. 4.2", page=12,
                 text="Hallmarking of gold jewellery is applicable under this scheme.",
                 source_url="https://bis.gov.in/is1417"):
    return {
        "relevance_score": 0.91,
        "standard_number": standard_number,
        "document_title": "IS 1417 Hallmarking of Gold Jewellery",
        "page_number": page,
        "section": section,
        "chunk_text": text,
        "source_url": source_url,
    }


def _gemini_response(payload: dict):
    mock_resp = MagicMock()
    mock_resp.text = json.dumps(payload)
    return mock_resp


class TestRelevantQuestion:
    """A. Relevant hallmarking question: retrieves evidence, produces a
    grounded answer, returns correct citations."""

    @patch("services.hallmarking_service.client")
    @patch("services.hallmarking_service.search_chunks")
    def test_grounded_answer_with_citations(self, mock_search, mock_client):
        chunk = _fake_chunk()
        mock_search.return_value = [chunk]
        mock_client.models.generate_content.return_value = _gemini_response({
            "status": "supported_by_evidence",
            "answer": "Hallmarking of gold jewellery is applicable under this scheme.",
            "key_points": [
                {"text": "The scheme applies to gold jewellery.", "evidence_refs": [1]}
            ],
            "next_steps": [
                {"text": "Check the item for the required marks.", "evidence_refs": [1]}
            ],
            "asserts_mandatory": False,
        })

        result = hs.get_hallmarking_help(db=MagicMock(), question="What does hallmarking mean?")

        assert result["status"] == hs.STATUS_SUPPORTED
        assert "hallmarking" in result["answer"].lower()
        assert result["key_points"] == ["The scheme applies to gold jewellery."]
        assert result["next_steps"] == ["Check the item for the required marks."]
        assert result["citations"] == [{
            "source_reference": "IS 1417, Cl. 4.2",
            "source_url": "https://bis.gov.in/is1417",
        }]


class TestInsufficientEvidence:
    """B. Unsupported hallmarking question: returns the exact fail-safe
    message, does not fabricate citations."""

    @patch("services.hallmarking_service.search_chunks")
    def test_no_retrieved_chunks(self, mock_search):
        mock_search.return_value = []

        result = hs.get_hallmarking_help(db=MagicMock(), question="Something totally unrelated")

        assert result["status"] == hs.STATUS_INSUFFICIENT
        assert result["answer"] == hs.INSUFFICIENT_EVIDENCE_MSG
        assert result["citations"] == []

    @patch("services.hallmarking_service.client")
    @patch("services.hallmarking_service.search_chunks")
    def test_gemini_reports_insufficient(self, mock_search, mock_client):
        mock_search.return_value = [_fake_chunk()]
        mock_client.models.generate_content.return_value = _gemini_response({
            "status": "insufficient_evidence",
            "answer": hs.INSUFFICIENT_EVIDENCE_MSG,
            "key_points": [],
            "next_steps": [],
            "asserts_mandatory": False,
        })

        result = hs.get_hallmarking_help(db=MagicMock(), question="Very edge-case question")

        assert result["status"] == hs.STATUS_INSUFFICIENT
        assert result["answer"] == hs.INSUFFICIENT_EVIDENCE_MSG
        assert result["citations"] == []


class TestHallucinatedStandardRejection:
    """C. Simulated Gemini output contains an unsupported IS number; it must
    not survive validation."""

    @patch("services.hallmarking_service.client")
    @patch("services.hallmarking_service.search_chunks")
    def test_unsupported_standard_number_rejected(self, mock_search, mock_client):
        # Only IS 1417 was actually retrieved.
        mock_search.return_value = [_fake_chunk(standard_number="IS 1417")]
        mock_client.models.generate_content.return_value = _gemini_response({
            "status": "supported_by_evidence",
            "answer": "This is also governed by IS 9999, a completely different standard.",
            "key_points": [{"text": "See IS 9999 for details.", "evidence_refs": [1]}],
            "next_steps": [],
            "asserts_mandatory": False,
        })

        result = hs.get_hallmarking_help(db=MagicMock(), question="What standard applies?")

        assert result["status"] == hs.STATUS_INSUFFICIENT
        assert result["answer"] == hs.INSUFFICIENT_EVIDENCE_MSG


class TestUnsupportedMandatoryClaim:
    """D. Simulated Gemini claims hallmarking is legally mandatory; if
    retrieved evidence does not explicitly support that claim, it must be
    rejected/downgraded."""

    @patch("services.hallmarking_service.client")
    @patch("services.hallmarking_service.search_chunks")
    def test_mandatory_claim_without_evidence_support_is_rejected(self, mock_search, mock_client):
        # Evidence text contains NO mandatory-language keywords.
        chunk = _fake_chunk(text="Hallmarking of gold jewellery is applicable under this scheme.")
        mock_search.return_value = [chunk]
        mock_client.models.generate_content.return_value = _gemini_response({
            "status": "supported_by_evidence",
            "answer": "Hallmarking is mandatory for all gold jewellery sold in India.",
            "key_points": [{"text": "It is a mandatory legal requirement.", "evidence_refs": [1]}],
            "next_steps": [],
            "asserts_mandatory": True,
        })

        result = hs.get_hallmarking_help(db=MagicMock(), question="Is hallmarking mandatory?")

        assert result["status"] == hs.STATUS_INSUFFICIENT
        assert result["answer"] == hs.INSUFFICIENT_EVIDENCE_MSG

    @patch("services.hallmarking_service.client")
    @patch("services.hallmarking_service.search_chunks")
    def test_mandatory_claim_with_evidence_support_is_allowed(self, mock_search, mock_client):
        # Evidence text DOES contain explicit mandatory language this time.
        chunk = _fake_chunk(text="Hallmarking is mandatory for gold jewellery under this scheme.")
        mock_search.return_value = [chunk]
        mock_client.models.generate_content.return_value = _gemini_response({
            "status": "supported_by_evidence",
            "answer": "Hallmarking is mandatory for gold jewellery under this scheme.",
            "key_points": [{"text": "It is a mandatory requirement per the evidence.", "evidence_refs": [1]}],
            "next_steps": [],
            "asserts_mandatory": True,
        })

        result = hs.get_hallmarking_help(db=MagicMock(), question="Is hallmarking mandatory?")

        assert result["status"] == hs.STATUS_SUPPORTED
        assert "mandatory" in result["answer"].lower()


class TestHallmarkSpecificHallucinationProtection:
    """E. Simulated Gemini invents a hallmark symbol/code/purity requirement
    not present in the evidence — must not be presented as fact. Modelled
    here as an ungrounded key point (no valid evidence_refs), which Safety
    Net 1 strips before it reaches the user."""

    @patch("services.hallmarking_service.client")
    @patch("services.hallmarking_service.search_chunks")
    def test_ungrounded_symbol_claim_is_stripped(self, mock_search, mock_client):
        chunk = _fake_chunk()
        mock_search.return_value = [chunk]
        mock_client.models.generate_content.return_value = _gemini_response({
            "status": "supported_by_evidence",
            "answer": "You should check the hallmark on your jewellery.",
            "key_points": [
                {"text": "Look for the BIS logo, purity in karat, and a 6-digit HUID code.", "evidence_refs": []},
            ],
            "next_steps": [],
            "asserts_mandatory": False,
        })

        result = hs.get_hallmarking_help(db=MagicMock(), question="How do I read a hallmark?")

        # The ungrounded key point (empty evidence_refs) must be dropped.
        assert result["key_points"] == []
        assert result["status"] == hs.STATUS_SUPPORTED


class TestCitationCorrectness:
    """F. Returned citations correspond to actual retrieved database chunks."""

    @patch("services.hallmarking_service.client")
    @patch("services.hallmarking_service.search_chunks")
    def test_citations_match_retrieved_chunks_exactly(self, mock_search, mock_client):
        chunk_a = _fake_chunk(standard_number="IS 1417", section="Cl. 4.2", page=12,
                               source_url="https://bis.gov.in/is1417")
        chunk_b = _fake_chunk(standard_number="IS 1417", section="Cl. 5.1", page=15,
                               source_url="https://bis.gov.in/is1417")
        mock_search.return_value = [chunk_a, chunk_b]
        mock_client.models.generate_content.return_value = _gemini_response({
            "status": "supported_by_evidence",
            "answer": "Grounded answer using both excerpts.",
            "key_points": [{"text": "Point one.", "evidence_refs": [1, 2]}],
            "next_steps": [],
            "asserts_mandatory": False,
        })

        result = hs.get_hallmarking_help(db=MagicMock(), question="Explain hallmarking clauses")

        assert len(result["citations"]) == 2
        assert result["citations"][0]["source_url"] == "https://bis.gov.in/is1417"
        assert result["citations"][0]["source_reference"] == "IS 1417, Cl. 4.2"
        assert result["citations"][1]["source_reference"] == "IS 1417, Cl. 5.1"


class TestExistingApiRegression:
    """G. Existing routes remain functional. Uses the shared
    client_with_mock_db fixture from conftest.py — get_db is overridden to
    a MagicMock session, and Gemini/search_chunks are mocked the same way
    as the service-level tests above, so this never touches a real DB or
    the live Gemini API."""

    @patch("services.hallmarking_service.client")
    @patch("services.hallmarking_service.search_chunks")
    def test_existing_routes_still_respond(self, mock_search, mock_client, client_with_mock_db):
        client, mock_db = client_with_mock_db

        chunk = _fake_chunk()
        mock_search.return_value = [chunk]
        mock_client.models.generate_content.return_value = _gemini_response({
            "status": "supported_by_evidence",
            "answer": "Hallmarking of gold jewellery is applicable under this scheme.",
            "key_points": [{"text": "The scheme applies to gold jewellery.", "evidence_refs": [1]}],
            "next_steps": [],
            "asserts_mandatory": False,
        })

        response = client.post(
            "/api/hallmarking/help",
            json={"question": "What does hallmarking mean?"},
        )
        assert response.status_code == 200
        body = response.json()
        assert body["status"] == "supported_by_evidence"
        assert "hallmarking" in body["answer"].lower()

        # validation still enforced on this route
        validation_response = client.post("/api/hallmarking/help", json={})
        assert validation_response.status_code == 422

        # a sibling route on the same app instance is still reachable
        # (light smoke check that adding this route didn't break routing)
        root_response = client.get("/")
        assert root_response.status_code == 200