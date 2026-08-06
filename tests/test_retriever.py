"""Tests for the RAG retriever: code extraction and relevant-chunk retrieval."""
from __future__ import annotations

from app.rag.retriever import extract_code, retriever


def test_extract_code_from_plain_code():
    assert extract_code("P0300") == "P0300"


def test_extract_code_normalizes_short_form():
    assert extract_code("P300") == "P0300"


def test_extract_code_returns_none_for_symptom_only():
    assert extract_code("car shakes at idle") is None


def test_retrieve_by_exact_code_returns_matching_chunks():
    results = retriever.retrieve("P0300", top_k=4)
    assert len(results) > 0
    assert all(r.code == "P0300" for r in results)


def test_retrieve_by_symptom_finds_relevant_code():
    results = retriever.retrieve("rotten egg smell from exhaust", top_k=5)
    assert len(results) > 0
    codes = [r.code for r in results]
    assert "P0420" in codes


def test_retrieve_returns_scores_sorted_descending():
    results = retriever.retrieve("P0171", top_k=4)
    scores = [r.score for r in results]
    assert scores == sorted(scores, reverse=True)
