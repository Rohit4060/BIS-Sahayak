"""
Automated tests for labs_service.py — the deterministic (no-LLM) laboratory
lookup used by POST /api/labs/find. These tests use a mocked DB session; they
do NOT hit a real database, and there is no Gemini call to mock since this
service is intentionally LLM-free.
"""
from unittest.mock import MagicMock

from labs_service import find_labs
from models import Laboratory


def _fake_lab(**overrides):
    """Builds a Laboratory-like object with sensible defaults, so each
    test only needs to specify the fields it cares about."""
    defaults = dict(
        name="Test Electrical Testing Lab",
        location="Delhi",
        capabilities="electrical safety testing, cable insulation testing",
        standard_numbers="IS 302 (Part 1) : 2024",
        accreditation_info="NABL accredited per IS/ISO/IEC 17025",
        source_url="https://example.com/labs-list",
        source_reference="BIS Recognized Labs List 2024",
    )
    defaults.update(overrides)
    lab = MagicMock(spec=Laboratory)
    for key, value in defaults.items():
        setattr(lab, key, value)
    return lab


def _mock_db_returning(labs):
    """Builds a mock DB session whose query().filter().limit().all()
    chain returns the given list, mirroring how find_labs uses it."""
    db = MagicMock()
    query_chain = db.query.return_value.filter.return_value.limit.return_value
    query_chain.all.return_value = labs
    return db


def test_find_labs_empty_table_returns_empty_list():
    """FAIL-SAFE PATH: mirrors the actual current state of the laboratories
    table (empty, no ingestion pipeline yet). With no matching rows,
    find_labs must return [] rather than inventing anything."""
    db = _mock_db_returning([])

    results = find_labs(db, "electrical cable")

    assert results == []


def test_find_labs_returns_matching_rows_on_description_only():
    """SUCCESS PATH: proves that once real laboratory data is ingested,
    find_labs correctly returns matching rows using product_description
    alone (no standard_number given)."""
    lab = _fake_lab()
    db = _mock_db_returning([lab])

    results = find_labs(db, "electrical cable")

    assert results == [lab]
    assert results[0].name == "Test Electrical Testing Lab"


def test_find_labs_returns_matching_rows_with_standard_number_filter():
    """SUCCESS PATH: when standard_number is also given, it's passed through
    as an additional filter alongside product_description."""
    lab = _fake_lab()
    db = _mock_db_returning([lab])

    results = find_labs(db, "electrical cable", standard_number="IS 302")

    assert results == [lab]
    db.query.return_value.filter.assert_called_once()


def test_find_labs_blank_description_returns_empty_list_without_hitting_db():
    """EDGE CASE: a blank/whitespace-only product_description should
    short-circuit before touching the database at all, regardless of
    whether standard_number is given."""
    db = MagicMock()

    results = find_labs(db, "   ", standard_number="IS 302")

    assert results == []
    db.query.assert_not_called()