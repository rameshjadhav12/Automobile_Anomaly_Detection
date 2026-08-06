# Cost & Latency Considerations — Service Center Usage

This document estimates cost and latency for running the Automotive GenAI
Diagnostics Assistant at a typical dealership / service-center scale, and the
levers available to tune both.

## 1. Usage Assumptions

| Parameter | Assumption |
|---|---|
| Service centers | 1 pilot center, ~15 concurrent bays |
| Queries/day/center | ~150 (diagnostic code or symptom lookups) |
| Peak concurrency | 5–10 simultaneous requests |
| Avg. query tokens | ~150 input tokens (query + retrieved context) |
| Avg. response tokens | ~300 output tokens (causes + steps + citations) |
| Retrieved chunks (`TOP_K`) | 4 chunks × ~200 tokens each |

## 2. Latency Budget (per `/diagnose` request)

| Stage | Typical latency | Notes |
|---|---|---|
| Embedding the query | 5–30 ms (local `sentence-transformers`) / 50–150 ms (OpenAI embeddings API) | Controlled by `USE_OPENAI_EMBEDDINGS` |
| Vector similarity search (FAISS, in-memory) | < 5 ms for a few thousand chunks | Chroma adds slight overhead for persistence but is comparable at this scale |
| Prompt assembly + service recommender | < 5 ms | Pure Python, no I/O |
| LLM generation call | 800 ms – 2.5 s | Dominant cost; depends on model + output length |
| Logging / feedback write | < 5 ms | Async-safe file/DB append |
| **Total (P50)** | **~1–2.5 s** | Acceptable for interactive service-bay use |
| **Total (P95, cold start / retry)** | **~4–6 s** | Includes one retry on transient LLM timeout |

Mitigations:
- Keep `TOP_K` small (3–5) — larger context increases both LLM latency and cost
  with diminishing retrieval-quality returns.
- Use a smaller/faster managed model (e.g. `gpt-4o-mini`) for the default
  path; reserve larger models for an optional "deep diagnosis" mode.
- Cache embeddings for the static manual corpus at ingest time (already done
  via `app/rag/ingest.py`) — never re-embed manuals on the request path.
- Local `sentence-transformers` embeddings avoid a network round-trip and are
  recommended for on-prem/service-center deployments with modest hardware.

## 3. Cost Estimate (Managed LLM Endpoint)

Assuming a `gpt-4o-mini`-class managed endpoint (~$0.15 / 1M input tokens,
~$0.60 / 1M output tokens as an illustrative rate — confirm against the actual
contracted pricing):

| Item | Value |
|---|---|
| Input tokens/request (query + 4 chunks + system prompt) | ~1,000 |
| Output tokens/request | ~300 |
| Cost/request | ≈ $0.00015 + $0.00018 ≈ **$0.00033** |
| Requests/day (1 center) | 150 |
| **Daily LLM cost (1 center)** | **≈ $0.05** |
| **Monthly LLM cost (1 center)** | **≈ $1.50** |
| Scaled to 50 centers | **≈ $75/month** |

Additional infrastructure cost drivers:
- **Compute**: 2 small containers (API + UI), e.g. 0.5 vCPU / 1 GB RAM each —
  low cost on Cloud Run / Fargate / AKS with autoscaling to zero off-hours.
- **Storage**: FAISS index + manuals corpus is small (synthetic dataset is a
  few MB); persistent volume cost is negligible.
- **Embeddings**: local `sentence-transformers` model = one-time compute
  cost, no per-query API fee. OpenAI embeddings add a small per-query fee if
  enabled.
- **Logging/monitoring**: flat-file or lightweight DB logging; cost scales
  with retention period, not per-request compute.

## 4. Scaling Levers

| Lever | Cost impact | Latency impact |
|---|---|---|
| Reduce `TOP_K` | ↓ input tokens, ↓ cost | ↓ latency |
| Smaller managed model | ↓ cost significantly | ↓ latency |
| Local embeddings vs API embeddings | ↓ cost, removes network hop | ↓ latency |
| Autoscale containers to zero off-hours | ↓ compute cost | Cold-start latency on first request |
| Response caching for repeated diagnostic codes | ↓ LLM calls for common codes (e.g. `P0300`, `P0420`) | ↓ latency for cache hits |
| Confidence threshold (`CONFIDENCE_THRESHOLD`) | Avoids wasted LLM calls when retrieval is poor — returns fallback instead | ↓ latency for low-confidence queries |

## 5. Summary

At pilot scale (1 service center), both compute and LLM token costs are
low (low single-digit dollars/month), with interactive latency around 1–2.5s
per query — well within acceptable bounds for a service-bay workflow. The
architecture scales near-linearly with the number of centers and query
volume, and the confidence-threshold fallback keeps costs bounded by avoiding
LLM calls when retrieval quality is too low to produce a grounded answer.
