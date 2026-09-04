"""Offline tests for /api/chat Gemini primary/fallback generation."""
from unittest.mock import MagicMock, patch

from services import rag_service


class GeminiProviderError(Exception):
    def __init__(self, code, message):
        super().__init__(message)
        self.code = code


def _chunk():
    return {
        "relevance_score": 0.95,
        "standard_number": "IS 302 Part 1:2024",
        "document_title": "Test BIS standard",
        "page_number": 8,
        "section": "Clause 4.2",
        "chunk_text": "IS 302 Part 1:2024 Clause 4.2 applies to this evidence.",
        "source_url": "https://example.test/is-302",
    }


def _response(text):
    response = MagicMock()
    response.text = text
    return response


@patch("services.rag_service.fallback_client")
@patch("services.rag_service.client")
@patch("services.rag_service.search_chunks")
def test_primary_success_does_not_call_fallback(mock_search, mock_primary, mock_fallback):
    mock_search.return_value = [_chunk()]
    mock_primary.models.generate_content.return_value = _response("Grounded answer [1].")

    result = rag_service.get_rag_response(MagicMock(), "What applies?", "en")

    assert result["answer"] == "Grounded answer [1]."
    mock_primary.models.generate_content.assert_called_once()
    mock_fallback.models.generate_content.assert_not_called()
    assert mock_primary.models.generate_content.call_args.kwargs["model"] == rag_service.PRIMARY_MODEL


@patch("services.rag_service.fallback_client")
@patch("services.rag_service.client")
@patch("services.rag_service.search_chunks")
def test_primary_incomplete_markdown_response_retries_then_fallback_returns_grounded_answer(
    mock_search, mock_primary, mock_fallback
):
    """The observed trailing escaped bullet must never be accepted or cited."""
    mock_search.return_value = [_chunk()]
    incomplete = "Based on the evidence [1]:\n\\* Power Input & Current\n\\* Heating\n\\*"
    mock_primary.models.generate_content.side_effect = [_response(incomplete), _response(incomplete)]
    mock_fallback.models.generate_content.return_value = _response(
        "IS 302 Part 1:2024 covers the available safety evidence [1]."
    )

    result = rag_service.get_rag_response(MagicMock(), "What applies?", "en")

    assert result["answer"] == "IS 302 Part 1:2024 covers the available safety evidence [1]."
    assert result["citations"] == rag_service._build_citations(mock_search.return_value)
    assert mock_primary.models.generate_content.call_count == 2
    mock_fallback.models.generate_content.assert_called_once()


@patch("services.rag_service.fallback_client")
@patch("services.rag_service.client")
@patch("services.rag_service.search_chunks")
def test_empty_or_incomplete_outputs_from_both_models_return_safe_response(
    mock_search, mock_primary, mock_fallback
):
    mock_search.return_value = [_chunk()]
    mock_primary.models.generate_content.return_value = _response("")
    mock_fallback.models.generate_content.return_value = _response("\\*")

    result = rag_service.get_rag_response(MagicMock(), "What applies?", "en")

    assert result == {"answer": rag_service.INSUFFICIENT_EVIDENCE_MSG, "citations": []}
    assert mock_primary.models.generate_content.call_count == 2
    assert mock_fallback.models.generate_content.call_count == 2


@patch("services.rag_service.time.sleep")
@patch("services.rag_service.fallback_client")
@patch("services.rag_service.client")
@patch("services.rag_service.search_chunks")
def test_resource_exhausted_429_retries_primary_then_uses_fallback_with_same_evidence_and_config(
    mock_search, mock_primary, mock_fallback, mock_sleep
):
    mock_search.return_value = [_chunk()]
    mock_primary.models.generate_content.side_effect = [
        GeminiProviderError(429, "RESOURCE_EXHAUSTED"),
        GeminiProviderError(429, "RESOURCE_EXHAUSTED"),
    ]
    mock_fallback.models.generate_content.return_value = _response("Grounded fallback answer [1].")

    result = rag_service.get_rag_response(MagicMock(), "What applies?", "en")

    assert result["answer"] == "Grounded fallback answer [1]."
    primary_call = mock_primary.models.generate_content.call_args.kwargs
    fallback_call = mock_fallback.models.generate_content.call_args.kwargs
    assert fallback_call["model"] == rag_service.FALLBACK_MODEL
    assert fallback_call["contents"] == primary_call["contents"]
    assert fallback_call["config"] is primary_call["config"]
    assert result["citations"] == rag_service._build_citations(mock_search.return_value)
    assert mock_primary.models.generate_content.call_count == 2
    mock_sleep.assert_called_once_with(rag_service.RETRY_DELAY_SECONDS)


@patch("services.rag_service.time.sleep")
@patch("services.rag_service.fallback_client")
@patch("services.rag_service.client")
@patch("services.rag_service.search_chunks")
def test_unavailable_503_retries_primary_before_fallback(mock_search, mock_primary, mock_fallback, mock_sleep):
    mock_search.return_value = [_chunk()]
    mock_primary.models.generate_content.side_effect = [
        GeminiProviderError(503, "UNAVAILABLE"),
        GeminiProviderError(503, "UNAVAILABLE"),
    ]
    mock_fallback.models.generate_content.return_value = _response("Grounded fallback answer [1].")

    result = rag_service.get_rag_response(MagicMock(), "What applies?", "en")

    assert result["answer"] == "Grounded fallback answer [1]."
    mock_fallback.models.generate_content.assert_called_once()
    assert mock_primary.models.generate_content.call_count == 2
    mock_sleep.assert_called_once_with(rag_service.RETRY_DELAY_SECONDS)


@patch("services.rag_service.time.sleep")
@patch("services.rag_service.fallback_client")
@patch("services.rag_service.client")
@patch("services.rag_service.search_chunks")
def test_retryable_primary_failure_can_succeed_without_fallback(
    mock_search, mock_primary, mock_fallback, mock_sleep
):
    mock_search.return_value = [_chunk()]
    mock_primary.models.generate_content.side_effect = [
        GeminiProviderError(503, "UNAVAILABLE"),
        _response("Grounded primary retry answer [1]."),
    ]

    result = rag_service.get_rag_response(MagicMock(), "What applies?", "en")

    assert result["answer"] == "Grounded primary retry answer [1]."
    mock_fallback.models.generate_content.assert_not_called()
    mock_sleep.assert_called_once_with(rag_service.RETRY_DELAY_SECONDS)


@patch("services.rag_service.fallback_client")
@patch("services.rag_service.client")
@patch("services.rag_service.search_chunks")
def test_non_retryable_primary_error_does_not_call_fallback(
    mock_search, mock_primary, mock_fallback
):
    mock_search.return_value = [_chunk()]
    mock_primary.models.generate_content.side_effect = GeminiProviderError(400, "INVALID_ARGUMENT")

    try:
        rag_service.get_rag_response(MagicMock(), "What applies?", "en")
    except GeminiProviderError:
        pass
    else:
        raise AssertionError("The non-retryable provider error should propagate.")

    mock_fallback.models.generate_content.assert_not_called()


@patch("services.rag_service.time.sleep")
@patch("services.rag_service.fallback_client")
@patch("services.rag_service.client")
@patch("services.rag_service.search_chunks")
def test_fallback_output_still_uses_existing_evidence_validation(
    mock_search, mock_primary, mock_fallback, mock_sleep
):
    mock_search.return_value = [_chunk()]
    mock_primary.models.generate_content.side_effect = [
        GeminiProviderError(429, "RESOURCE_EXHAUSTED"),
        GeminiProviderError(429, "RESOURCE_EXHAUSTED"),
    ]
    mock_fallback.models.generate_content.return_value = _response("This is covered by IS 9999 [1].")

    result = rag_service.get_rag_response(MagicMock(), "What applies?", "en")

    assert result == {
        "answer": rag_service.INSUFFICIENT_EVIDENCE_MSG,
        "citations": [],
    }


@patch("services.rag_service.time.sleep")
@patch("services.rag_service.fallback_client")
@patch("services.rag_service.client")
@patch("services.rag_service.search_chunks")
def test_both_generation_attempts_fail_and_chat_returns_existing_safe_response(
    mock_search, mock_primary, mock_fallback, mock_sleep, client_with_mock_db
):
    client, _ = client_with_mock_db
    mock_search.return_value = [_chunk()]
    mock_primary.models.generate_content.side_effect = [
        GeminiProviderError(429, "RESOURCE_EXHAUSTED"),
        GeminiProviderError(429, "RESOURCE_EXHAUSTED"),
    ]
    mock_fallback.models.generate_content.side_effect = [
        GeminiProviderError(503, "UNAVAILABLE"),
        GeminiProviderError(503, "UNAVAILABLE"),
    ]

    response = client.post("/api/chat", json={"message": "What applies?", "language": "en"})

    assert response.status_code == 200
    assert response.json() == {
        "reply": "Sorry, Sahayak's AI service is having trouble right now. Please try again in a moment.",
        "citations": [],
    }
    assert mock_primary.models.generate_content.call_count == 2
    assert mock_fallback.models.generate_content.call_count == 2
    assert mock_sleep.call_count == 2
