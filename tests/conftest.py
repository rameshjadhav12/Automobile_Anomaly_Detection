"""Pytest fixtures shared across the test suite.

Ensures a vector index exists before tests that depend on retrieval run, by building
it once per test session directly (fast: TF-IDF over ~10 small synthetic manuals).
"""
from __future__ import annotations

import pytest

from app.core.config import settings


@pytest.fixture(scope="session", autouse=True)
def ensure_index_built():
    manifest_path = settings.vectorstore_path / "manifest.json"
    if not manifest_path.exists():
        from app.rag.ingest import build_index

        build_index()
    yield
