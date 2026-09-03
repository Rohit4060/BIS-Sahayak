"""
Shared pytest fixtures for route-level (API) tests across this project.

client_with_mock_db provides a FastAPI TestClient wired to the real `app`,
with get_db overridden to yield a MagicMock session instead of a real
Postgres connection — so route tests never touch a real database. Combine
with @patch on the relevant service's Gemini client / search_chunks (as the
service-level tests already do) to keep route tests fully offline.
"""
import pytest
from unittest.mock import MagicMock
from fastapi.testclient import TestClient

from main import app
from database import get_db


@pytest.fixture
def client_with_mock_db():
    mock_db = MagicMock()

    def _override_get_db():
        yield mock_db

    app.dependency_overrides[get_db] = _override_get_db
    yield TestClient(app), mock_db
    app.dependency_overrides.clear()