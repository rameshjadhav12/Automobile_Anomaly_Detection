"""End-to-end diagnose workflow: retrieve -> ground -> explain -> recommend -> cite -> log.

This is the "tool-like workflow" referenced in the assignment: retrieval and the
service-recommendation step are deterministic tools, while the LLM is only responsible
for the grounded natural-language explanation.
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from functools import lru_cache
from typing import Any, Literal, TypedDict

from langgraph.graph import END, StateGraph

from app.core.config import settings
from app.core.logging_config import log_diagnostic_interaction
from app.llm.client import llm_client
from app.rag.retriever import extract_code, retriever
from app.workflow.service_recommender import recommend_service_action

FALLBACK_MESSAGE = (
    "I don't have enough information in the service manuals to answer this confidently. "
    "Please consult a certified technician or provide the exact diagnostic code."
)


@dataclass
class Citation:
    doc_file: str
    heading: str
    code: str
    score: float


@dataclass
class DiagnoseResult:
    query: str
    matched_code: str | None
    is_fallback: bool
    confidence: float
    explanation: str
    service_recommendation: dict
    citations: list[Citation] = field(default_factory=list)


class DiagnoseState(TypedDict, total=False):
    query: str
    code: str | None
    prompt_version: str | None
    chunks: list[Any]
    confidence: float
    matched_code: str | None
    explanation: str
    service_recommendation: dict
    citations: list[Citation]
    result: DiagnoseResult


@lru_cache(maxsize=1)
def _load_code_metadata() -> dict[str, dict]:
    with settings.diagnostic_codes_path.open("r", encoding="utf-8") as f:
        codes = json.load(f)
    return {entry["code"]: entry for entry in codes}


def _retrieve_context(state: DiagnoseState) -> DiagnoseState:
    query = state["query"]
    chunks = retriever.retrieve(query, top_k=settings.top_k, code_filter=state.get("code"))
    confidence = max((chunk.score for chunk in chunks), default=0.0)
    matched_code = state.get("code") or (chunks[0].code if chunks else extract_code(query))
    return {"chunks": chunks, "confidence": confidence, "matched_code": matched_code}


def _route_after_retrieval(state: DiagnoseState) -> Literal["fallback", "answer"]:
    chunks = state.get("chunks", [])
    confidence = state.get("confidence", 0.0)
    if not chunks or confidence < settings.confidence_threshold:
        return "fallback"
    return "answer"


def _build_fallback(state: DiagnoseState) -> DiagnoseState:
    result = DiagnoseResult(
        query=state["query"],
        matched_code=state.get("matched_code"),
        is_fallback=True,
        confidence=state.get("confidence", 0.0),
        explanation=FALLBACK_MESSAGE,
        service_recommendation=recommend_service_action(None),
        citations=[],
    )
    return {"result": result}


def _generate_answer(state: DiagnoseState) -> DiagnoseState:
    chunks = state.get("chunks", [])
    matched_code = state.get("matched_code")
    explanation = llm_client.answer(state["query"], chunks, prompt_version=state.get("prompt_version"))
    code_meta = _load_code_metadata().get(matched_code or "")
    citations = [
        Citation(doc_file=chunk.doc_file, heading=chunk.heading, code=chunk.code, score=round(chunk.score, 4))
        for chunk in chunks
    ]
    result = DiagnoseResult(
        query=state["query"],
        matched_code=matched_code,
        is_fallback=False,
        confidence=state.get("confidence", 0.0),
        explanation=explanation,
        service_recommendation=recommend_service_action(code_meta),
        citations=citations,
    )
    return {"explanation": explanation, "citations": citations, "result": result}


@lru_cache(maxsize=1)
def _diagnose_graph():
    graph = StateGraph(DiagnoseState)
    graph.add_node("retrieve_context", _retrieve_context)
    graph.add_node("build_fallback", _build_fallback)
    graph.add_node("generate_answer", _generate_answer)
    graph.set_entry_point("retrieve_context")
    graph.add_conditional_edges(
        "retrieve_context",
        _route_after_retrieval,
        {"fallback": "build_fallback", "answer": "generate_answer"},
    )
    graph.add_edge("build_fallback", END)
    graph.add_edge("generate_answer", END)
    return graph.compile()


def diagnose(query: str, code: str | None = None, prompt_version: str | None = None) -> DiagnoseResult:
    query = query.strip()
    final_state = _diagnose_graph().invoke({"query": query, "code": code, "prompt_version": prompt_version})
    result = final_state["result"]

    log_diagnostic_interaction(
        {
            "query": query,
            "matched_code": result.matched_code,
            "confidence": round(result.confidence, 4),
            "is_fallback": result.is_fallback,
            "retrieved_sources": [c.doc_file for c in result.citations],
            "response_summary": result.explanation[:500],
        }
    )

    return result
