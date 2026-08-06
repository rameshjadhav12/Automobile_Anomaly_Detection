"""Prompt version registry - central place to look up prompt builders by version string.

To add a new prompt version:
1. Create app/llm/prompts/v3.py with SYSTEM_PROMPT and build_user_prompt(query, chunks).
2. Register it in PROMPT_VERSIONS below.
3. Add an entry to PROMPT_CHANGELOG.md describing what changed and why.
4. Set PROMPT_VERSION=v3 in .env to activate it (or override per-request if needed).
"""
from __future__ import annotations

from app.llm.prompts import v1, v2

PROMPT_VERSIONS = {
    "v1": v1,
    "v2": v2,
}


def get_prompt_module(version: str):
    if version not in PROMPT_VERSIONS:
        raise ValueError(f"Unknown prompt version '{version}'. Available: {list(PROMPT_VERSIONS)}")
    return PROMPT_VERSIONS[version]
