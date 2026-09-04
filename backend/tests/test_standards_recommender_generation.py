"""Regression coverage for recommendation generation reliability reuse."""
import json
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from services import standards_recommender


def _chunk():
    return {
        "standard_number": "IS 302 (Part 1) : 2024/ IEC 60335-1 : 2020",
        "document_title": "HOUSEHOLD AND SIMILAR ELECTRICAL APPLIANCES - SAFETY",
        "page_number": 1,
        "section": None,
        "chunk_text": "Household and Similar Electrical Appliances - Safety Part 1 General Requirements.",
        "source_url": "https://www.bis.gov.in/302-1-2024-for-upload/?lang=en",
    }


@patch("services.standards_recommender._generate_answer")
@patch("services.standards_recommender.search_chunks")
def test_recommendations_use_shared_primary_fallback_generation_and_keep_db_citations(
    mock_search, mock_generate
):
    chunk = _chunk()
    mock_search.return_value = [chunk]
    mock_generate.return_value = SimpleNamespace(text=json.dumps({
        "recommendations": [{
            "standard_number": chunk["standard_number"],
            "relevance": "medium",
            "reason": "The retrieved title covers household electrical appliances [1].",
            "evidence_states_mandatory": False,
        }]
    }))

    result = standards_recommender.recommend_standards(MagicMock(), "household electrical appliance")

    user_message, config = mock_generate.call_args.args
    assert "PRODUCT DESCRIPTION: household electrical appliance" in user_message
    assert chunk["standard_number"] in user_message
    assert config.system_instruction == standards_recommender.SYSTEM_PROMPT
    assert config.response_mime_type == "application/json"
    assert result["recommendations"][0]["standard_number"] == chunk["standard_number"]
    assert result["recommendations"][0]["citations"] == [{
        "standard_number": chunk["standard_number"],
        "clause": None,
        "page": 1,
        "source_url": chunk["source_url"],
    }]
