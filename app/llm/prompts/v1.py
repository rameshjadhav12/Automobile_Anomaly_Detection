"""Prompt v1 - initial baseline prompt for diagnostic explanation.

Changelog: see PROMPT_CHANGELOG.md at the project root.
"""
from __future__ import annotations

from typing import Any, Iterable

SYSTEM_PROMPT = (
    "You are an automotive service assistant. Use only the provided service manual "
    "excerpts to explain the diagnostic code or symptom, list possible causes, and "
    "recommend next service steps."
)


def build_user_prompt(query: str, chunks: Iterable[Any]) -> str:
    context = "\n\n".join(f"[{c.doc_file}] {c.text}" for c in chunks)
    return (
        f"Customer query: {query}\n\n"
        f"Service manual context:\n{context}\n\n"
        "Explain possible causes and recommended next steps."
    )
