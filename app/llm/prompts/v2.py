"""Prompt v2 - grounded, structured-output prompt with explicit citation + fallback rules.

Changelog: see PROMPT_CHANGELOG.md at the project root.

Improvements over v1:
- Forces a fixed section structure (Possible Causes / Recommended Next Steps / Citations)
  so the FastAPI layer and Streamlit UI can render consistently.
- Explicit instruction to ground every claim in the provided context only, and to say so
  plainly when the context is insufficient (safety/fallback behavior).
- Each context excerpt is tagged with a citation id the model must reference.
"""
from __future__ import annotations

from typing import Any, Iterable

SYSTEM_PROMPT = (
    "You are an Automotive Service Assistant used by service center engineers. "
    "You must ONLY use the provided service manual excerpts as your source of truth - "
    "never invent causes, part numbers, or steps that are not supported by the context. "
    "If the context does not contain enough information to answer confidently, respond "
    "with exactly: 'I don't have enough information in the service manuals to answer "
    "this confidently. Please consult a certified technician or provide the exact "
    "diagnostic code.' "
    "Always reference the source excerpts you used by their citation id, e.g. [C1]."
)

RESPONSE_FORMAT_INSTRUCTIONS = (
    "Respond using exactly this structure:\n"
    "Possible Causes:\n- <cause 1> [C#]\n- <cause 2> [C#]\n\n"
    "Recommended Next Steps:\n1. <step 1> [C#]\n2. <step 2> [C#]\n\n"
    "Citations:\n[C#] <source document name>"
)


def build_user_prompt(query: str, chunks: Iterable[Any]) -> str:
    chunk_list = list(chunks)
    context_lines = []
    for i, c in enumerate(chunk_list, start=1):
        context_lines.append(f"[C{i}] Source: {c.doc_file} (section: {c.heading})\n{c.text}")
    context = "\n\n".join(context_lines) if context_lines else "(no relevant context retrieved)"

    return (
        f"Diagnostic query from service engineer: {query}\n\n"
        f"Retrieved service manual excerpts:\n{context}\n\n"
        f"{RESPONSE_FORMAT_INSTRUCTIONS}"
    )
