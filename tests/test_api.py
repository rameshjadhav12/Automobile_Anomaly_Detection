"""Tests for the FastAPI endpoints using an in-process TestClient (no network calls)."""
from __future__ import annotations

from fastapi.testclient import TestClient

from app.api.main import app

client = TestClient(app)


def test_health_endpoint():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_diagnose_endpoint_known_code():
    response = client.post("/diagnose", json={"query": "P0300"})
    assert response.status_code == 200
    body = response.json()
    assert body["matched_code"] == "P0300"
    assert body["is_fallback"] is False
    assert len(body["citations"]) > 0


def test_diagnose_endpoint_rejects_empty_query():
    response = client.post("/diagnose", json={"query": "   "})
    assert response.status_code == 400


def test_feedback_endpoint():
    response = client.post(
        "/feedback",
        json={"query": "P0300", "matched_code": "P0300", "rating": "up", "comment": "Helpful!"},
    )
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_monitoring_stats_endpoint():
    response = client.get("/monitoring/stats")
    assert response.status_code == 200
    body = response.json()
    assert "total_queries" in body
    assert "unresolved_rate" in body
