"""Tests for the diagnose workflow: grounded answers, fallback, and service recommendations."""
from __future__ import annotations

from app.workflow.diagnose_workflow import diagnose
from app.workflow.service_recommender import recommend_service_action


def test_diagnose_known_code_returns_grounded_answer():
    result = diagnose("P0300")
    assert result.is_fallback is False
    assert result.matched_code == "P0300"
    assert result.citations, "Expected at least one citation for a confidently matched code."
    assert "Possible Causes" in result.explanation


def test_diagnose_symptom_query_matches_expected_code():
    result = diagnose("rotten egg smell from exhaust and failed emissions test")
    assert result.matched_code == "P0420"
    assert result.is_fallback is False


def test_diagnose_nonsense_query_triggers_fallback():
    result = diagnose("purple elephant flying spaceship warp drive malfunction")
    assert result.is_fallback is True
    assert "don't have enough information" in result.explanation


def test_service_recommendation_critical_severity():
    rec = recommend_service_action({"severity": "Critical", "code": "U0100", "system": "Network"})
    assert rec["urgency"] == "Critical"


def test_service_recommendation_unknown_metadata_falls_back():
    rec = recommend_service_action(None)
    assert rec["urgency"] == "Unknown"
