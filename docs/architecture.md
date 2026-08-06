# Architecture & Deployment — Automotive GenAI Diagnostics Assistant

## 1. High-Level Component Architecture

```mermaid
flowchart LR
    subgraph Client
        U[Service Engineer / Advisor]
    end

    subgraph UI["Streamlit UI (Dockerfile.streamlit)"]
        S[streamlit_app/app.py]
    end

    subgraph API["FastAPI Service (Dockerfile.api)"]
        R1[/diagnose/]
        R2[/feedback/]
        R3[/monitoring/]
        WF[diagnose_workflow.py
      LangGraph]
        SR[service_recommender.py]
    end

    subgraph RAG["RAG Pipeline"]
        EMB[embeddings.py]
        RET[retriever.py
      Hybrid ranker]
        KW[keyword_search.py
      Keyword agent]
        VS[(Vector Store\nFAISS / Chroma)]
        ING[ingest.py]
    end

    subgraph LLM["LLM Layer"]
        CLI[llm/client.py]
        PR[prompt_registry.py\nv1 / v2 prompts]
        OPENAI[(Tekstac LLM Gateway\nClaude model IDs)]
    end

    subgraph DATA["Synthetic Data"]
        MAN[data/manuals_pdf/*.pdf\nPDF-first manuals]
        MDFB[data/manuals/*.md\nfallback demo manuals]
        CODES[data/diagnostic_codes.json]
    end

    subgraph OBS["Observability"]
        LOG[logging_config.py -> logs/]
        FB[feedback_store.py -> feedback_data/]
        MON[monitoring.py]
    end

    U --> S --> R1
    S --> R2
    S --> R3
    R1 --> WF
    WF --> SR
    WF --> RET
    RET --> KW
    RET --> VS
    RET --> EMB
    ING --> MAN
    ING --> MDFB
    ING --> CODES
    ING --> VS
    WF --> CLI
    CLI --> PR
    CLI --> OPENAI
    WF --> LOG
    R2 --> FB
    R3 --> MON
    MON --> LOG
    MON --> FB
```

## 2. Request Flow (Diagnose)

```mermaid
sequenceDiagram
    participant Eng as Service Engineer
    participant UI as Streamlit UI
    participant API as FastAPI /diagnose
    participant WF as Diagnose Workflow
    participant Ret as Retriever
    participant VS as Vector Store
    participant LLM as LLM Client
    participant Log as Logger

    Eng->>UI: Enter diagnostic code / symptom
    UI->>API: POST /diagnose {query}
    API->>WF: run(query)
    WF->>Ret: retrieve(query, top_k)
    Ret->>VS: vector similarity search(embedding)
    Ret->>Ret: keyword-search agent ranks lexical matches
    VS-->>Ret: vector chunks + scores
    Ret-->>Ret: blend vector and keyword scores
    Ret-->>WF: ranked chunks + confidence
    alt confidence below threshold
        WF-->>API: fallback "answer not found" response
    else confidence acceptable
        WF->>LLM: generate(prompt_version, query, context)
        LLM-->>WF: causes + next steps + citations
        WF->>WF: service_recommender (map causes -> service actions)
    end
    WF->>Log: log(code, sources, response, confidence)
    WF-->>API: DiagnoseResponse
    API-->>UI: JSON response
    UI-->>Eng: Render causes, steps, citations
```

## 3. Deployment Diagram

```mermaid
flowchart TB
    subgraph Internet
        Browser[Service Center Browser]
    end

    subgraph "Cloud VPC (e.g. AWS/Azure/GCP)"
        direction TB
        subgraph "Container Orchestration (ECS/AKS/Cloud Run)"
            UIC["UI Container\nstreamlit:8501"]
            APIC["API Container\nfastapi/uvicorn:8000"]
        end
        LB[Load Balancer / API Gateway + TLS]
        VOL[(Persistent Volume\nFAISS index / vectorstore-data)]
        LOGS[(Log & Feedback Volume\nlogs-data, feedback-data)]
        SECRETS[Secrets Manager\nOPENAI_API_KEY]
        LLMEP[Managed LLM Endpoint\nOpenAI / Azure OpenAI]
        MONS[Monitoring Stack\nCloudWatch / Azure Monitor / Prometheus+Grafana]
    end

    Browser -->|HTTPS| LB --> UIC
    UIC -->|internal HTTP| APIC
    APIC --> VOL
    APIC --> LOGS
    APIC -.reads secret.-> SECRETS
    APIC -->|HTTPS API call| LLMEP
    LOGS --> MONS
    APIC --> MONS
```

Local development mirrors this exactly via `docker-compose.yml`: the `api` and `ui`
services correspond to the two containers, named Docker volumes
(`vectorstore-data`, `logs-data`, `feedback-data`) stand in for the persistent
volume, and environment variables (`OPENAI_API_KEY`, `VECTOR_DB_BACKEND`, etc.)
stand in for the secrets manager / config map.

## 4. Managed LLM Endpoint Design

- **Provider abstraction**: [app/llm/client.py](../app/llm/client.py) wraps calls behind a single
  `LLMClient.generate()` interface. In production this targets a managed
  endpoint (`https://llmgw-wp.tekstac.com`) with configured Claude gateway model ids;
  locally, when
  `OPENAI_API_KEY` is unset, it transparently falls back to a deterministic
  mock generator so the demo and tests run offline.
- **Prompt version control**: prompts are versioned modules
  (`app/llm/prompts/v1.py`, `v2.py`) selected via `PROMPT_VERSION` env var and
  tracked in [PROMPT_CHANGELOG.md](../PROMPT_CHANGELOG.md), enabling safe rollout/rollback
  without code changes.
- **Resilience**: request timeouts + retry/backoff at the client layer;
  on repeated failure the workflow returns the safety/fallback response
  instead of raising to the UI.
- **Isolation**: the LLM endpoint is never called directly by the UI — all
  calls are proxied through the FastAPI service so API keys stay server-side.

## 5. Security Notes

- Secrets (`OPENAI_API_KEY`) are injected via environment variables / secrets
  manager, never committed (`.env` is gitignored, `.env.example` provided).
- API container runs as non-root where supported by the base image; only
  ports 8000 (API) and 8501 (UI) are exposed.
- The UI never talks to the LLM endpoint directly — only to the FastAPI
  service — keeping the API key out of the browser-facing tier.
- Input validation via Pydantic schemas (`app/api/schemas.py`) on all
  endpoints.
