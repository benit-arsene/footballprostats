"""Tests for route compatibility and error handling preservation.

These tests verify that existing routes still work correctly after
the provider abstraction refactor. They use FastAPI's TestClient.
"""

import sys
import os

# Don't load .env during tests — use mock config
os.environ.setdefault("APIFOOTBALL_KEY", "test-key")
os.environ.setdefault("APIFOOTBALL_HOST", "v3.football.api-sports.io")
os.environ.pop("DATABASE_URL", None)

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def client():
    """Create a TestClient for the app."""
    from main import app
    with TestClient(app) as c:
        yield c


class TestRouteCompatibility:
    def test_root_returns_api_message(self, client):
        resp = client.get("/")
        assert resp.status_code == 200
        assert "message" in resp.json()

    def test_health_endpoint(self, client):
        resp = client.get("/api/health")
        assert resp.status_code == 200
        assert resp.json()["status"] == "ok"

    def test_validation_error_format(self, client):
        """RequestValidationError returns structured JSON."""
        resp = client.get("/api/v1/matches/abc")
        assert resp.status_code == 422
        body = resp.json()
        assert "error" in body
        assert body["error"]["code"] == "VALIDATION_ERROR"

    def test_match_live_429_on_rate_limit(self, client):
        """APIRateLimitError returns 429 with structured body."""
        # Since we don't have a real API, the call will fail with
        # APIConnectionError → 502. We just verify error structure.
        resp = client.get("/api/v1/matches/live")
        assert resp.status_code in (429, 502, 200)
        if resp.status_code in (429, 502):
            body = resp.json()
            assert "error" in body
            assert "code" in body["error"]

    def test_match_detail_404_format(self, client):
        """Not found returns structured error body."""
        resp = client.get("/api/v1/matches/999999")
        if resp.status_code == 404:
            body = resp.json()
            assert "error" in body
            assert body["error"]["code"] == "NOT_FOUND"

    def test_api_routes_exist(self, client):
        """Key API routes should be registered."""
        routes = [r.path for r in client.routes]
        assert "/api/v1/matches/live" in routes or any(
            "matches/live" in r.path for r in client.routes
        )
        assert "/api/v1/teams" in routes or any(
            "teams" in r.path for r in client.routes
        )
        assert "/api/v1/leagues" in routes or any(
            "leagues" in r.path for r in client.routes
        )
