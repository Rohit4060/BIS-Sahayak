"""Offline tests for M15's multilingual extension of the existing /api/chat RAG path."""
from unittest.mock import MagicMock, patch

from services import rag_service


def _chunk(standard_number="IS 302 Part 1:2024", section="Clause 4.2"):
    return {
        "relevance_score": 0.95,
        "standard_number": standard_number,
        "document_title": "Test BIS standard",
        "page_number": 8,
        "section": section,
        "chunk_text": "IS 302 Part 1:2024 Clause 4.2 applies to this test evidence.",
        "source_url": "https://example.test/is-302",
    }


def _response(text):
    result = MagicMock()
    result.text = text
    return result


@patch("services.rag_service.client")
@patch("services.rag_service.search_chunks")
def test_english_chat_remains_grounded(mock_search, mock_client):
    mock_search.return_value = [_chunk()]
    mock_client.models.generate_content.return_value = _response("Grounded English answer [1].")

    result = rag_service.get_rag_response(MagicMock(), "What applies?", "en")

    assert result["answer"] == "Grounded English answer [1]."
    assert result["citations"][0]["standard_number"] == "IS 302 Part 1:2024"


@patch("services.rag_service.client")
@patch("services.rag_service.search_chunks")
def test_hindi_question_uses_existing_retrieval_and_requests_hindi(mock_search, mock_client):
    mock_search.return_value = [_chunk()]
    mock_client.models.generate_content.return_value = _response("यह उत्तर उपलब्ध साक्ष्य पर आधारित है [1]।")

    result = rag_service.get_rag_response(MagicMock(), "LED के लिए BIS मानक क्या है?", "hi")

    assert result["answer"].startswith("यह उत्तर")
    assert mock_search.call_args.args[1] == "LED के लिए BIS मानक क्या है?"
    system_instruction = mock_client.models.generate_content.call_args.kwargs["config"].system_instruction
    assert "FINAL RESPONSE LANGUAGE: Hindi (hi)" in system_instruction


@patch("services.rag_service.client")
@patch("services.rag_service.search_chunks")
def test_bengali_auto_detection_and_identifier_preservation(mock_search, mock_client):
    mock_search.return_value = [_chunk()]
    answer = "এই উত্তরটি IS 302 Part 1:2024-এর Clause 4.2 থেকে নেওয়া হয়েছে [1]।"
    mock_client.models.generate_content.return_value = _response(answer)

    result = rag_service.get_rag_response(MagicMock(), "LED-এর জন্য BIS মান কী?", None)

    assert result["answer"] == answer
    system_instruction = mock_client.models.generate_content.call_args.kwargs["config"].system_instruction
    assert "FINAL RESPONSE LANGUAGE: Bengali (bn)" in system_instruction
    assert "IS 302 Part 1:2024" in result["answer"]
    assert "Clause 4.2" in result["answer"]
    assert result["citations"][0]["source_url"] == "https://example.test/is-302"


@patch("services.rag_service.search_chunks")
def test_non_english_insufficient_evidence_is_localized(mock_search):
    mock_search.return_value = []

    result = rag_service.get_rag_response(MagicMock(), "यह प्रश्न उपलब्ध स्रोतों में नहीं है", "hi")

    assert result["answer"] == rag_service.INSUFFICIENT_EVIDENCE_MESSAGES["hi"]
    assert result["citations"] == []


@patch("services.rag_service.client")
@patch("services.rag_service.search_chunks")
def test_localized_model_insufficient_evidence_has_no_citations(mock_search, mock_client):
    mock_search.return_value = [_chunk()]
    mock_client.models.generate_content.return_value = _response(
        rag_service.INSUFFICIENT_EVIDENCE_MESSAGES["hi"]
    )

    result = rag_service.get_rag_response(MagicMock(), "यह प्रश्न असमर्थित है", "hi")

    assert result["answer"] == rag_service.INSUFFICIENT_EVIDENCE_MESSAGES["hi"]
    assert result["citations"] == []


@patch("services.rag_service.client")
@patch("services.rag_service.search_chunks")
def test_multilingual_hallucinated_standard_is_rejected(mock_search, mock_client):
    mock_search.return_value = [_chunk()]
    mock_client.models.generate_content.return_value = _response("यह IS 9999 के अंतर्गत आता है।")

    result = rag_service.get_rag_response(MagicMock(), "यह किस मानक पर लागू है?", "hi")

    assert result["answer"] == rag_service.INSUFFICIENT_EVIDENCE_MESSAGES["hi"]
    assert result["citations"] == []


@patch("services.rag_service.client")
@patch("services.rag_service.search_chunks")
def test_non_english_model_prose_is_rejected_if_it_ignores_requested_language(mock_search, mock_client):
    mock_search.return_value = [_chunk()]
    mock_client.models.generate_content.return_value = _response("English answer despite the Hindi request [1].")

    result = rag_service.get_rag_response(MagicMock(), "BIS मानक क्या है?", "hi")

    assert result["answer"] == rag_service.INSUFFICIENT_EVIDENCE_MESSAGES["hi"]
    assert result["citations"] == []


@patch("services.rag_service.client")
@patch("services.rag_service.search_chunks")
def test_standard_stem_validation_does_not_mutate_a_set_during_iteration(mock_search, mock_client):
    mock_search.return_value = [_chunk()]
    mock_client.models.generate_content.return_value = _response("यह IS 302 के Clause 4.2 पर आधारित है [1]।")

    result = rag_service.get_rag_response(MagicMock(), "यह कौन सा मानक है?", "hi")

    assert result["answer"].startswith("यह IS 302")
    assert result["citations"]


def test_api_rejects_unsupported_language(client_with_mock_db):
    client, _ = client_with_mock_db

    response = client.post("/api/chat", json={"message": "test", "language": "fr"})

    assert response.status_code == 422


@patch("services.rag_service.client")
@patch("services.rag_service.search_chunks")
def test_chat_api_passes_language_and_keeps_db_citations(mock_search, mock_client, client_with_mock_db):
    client, _ = client_with_mock_db
    mock_search.return_value = [_chunk()]
    mock_client.models.generate_content.return_value = _response("\u0ba4\u0bae\u0bbf\u0bb4\u0bcd \u0b86\u0ba4\u0bbe\u0bb0\u0baa\u0bc2\u0bb0\u0bcd\u0bb5 \u0baa\u0ba4\u0bbf\u0bb2\u0bcd [1]")

    response = client.post("/api/chat", json={"message": "BIS என்ன சொல்கிறது?", "language": "ta"})

    assert response.status_code == 200
    assert response.json()["citations"][0]["standard_number"] == "IS 302 Part 1:2024"
