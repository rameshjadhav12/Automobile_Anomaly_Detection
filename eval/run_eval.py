"""Evaluation script for diagnostic-code retrieval performance.

Computes Hit Rate@K and Mean Reciprocal Rank (MRR) against eval/eval_set.json,
and writes a report to eval/eval_report.json for tracking over time (retrieval
performance tracking requirement).

Run with:
    python -m eval.run_eval
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from app.core.config import settings
from app.rag.retriever import retriever

EVAL_SET_PATH = Path(__file__).resolve().parent / "eval_set.json"
EVAL_REPORT_PATH = Path(__file__).resolve().parent / "eval_report.json"


def load_eval_set() -> list[dict]:
    with EVAL_SET_PATH.open("r", encoding="utf-8") as f:
        return json.load(f)


def run_eval(top_k: int = 5) -> dict:
    eval_items = load_eval_set()
    hits = 0
    reciprocal_ranks = []
    per_query_results = []

    for item in eval_items:
        query = item["query"]
        expected_code = item["expected_code"]

        # Retrieve without forcing a code filter, so we measure real end-to-end retrieval
        # quality (including symptom-only queries where no code appears in the text).
        results = retriever.retrieve(query, top_k=top_k, code_filter=None)
        codes_in_order = [r.code for r in results]

        rank = next((i + 1 for i, c in enumerate(codes_in_order) if c == expected_code), None)
        hit = rank is not None
        hits += int(hit)
        reciprocal_ranks.append(1.0 / rank if rank else 0.0)

        per_query_results.append(
            {
                "query": query,
                "expected_code": expected_code,
                "retrieved_codes": codes_in_order,
                "hit": hit,
                "rank": rank,
            }
        )

    total = len(eval_items)
    hit_rate = hits / total if total else 0.0
    mrr = sum(reciprocal_ranks) / total if total else 0.0

    report = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "top_k": top_k,
        "num_queries": total,
        "hit_rate_at_k": round(hit_rate, 4),
        "mean_reciprocal_rank": round(mrr, 4),
        "per_query_results": per_query_results,
    }

    with EVAL_REPORT_PATH.open("w", encoding="utf-8") as f:
        json.dump(report, f, indent=2)

    print(f"Hit Rate@{top_k}: {hit_rate:.2%}")
    print(f"Mean Reciprocal Rank: {mrr:.4f}")
    print(f"Full report written to {EVAL_REPORT_PATH}")
    return report


if __name__ == "__main__":
    run_eval(top_k=settings.top_k + 1)
