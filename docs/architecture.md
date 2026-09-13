# Architecture

## The Lenny Growth Assistant

### High-Level Architecture

```text
+----------------+     +--------------+     +--------------+
¦  React+Vite UI ¦----?¦  FastAPI API  ¦----?¦  PostgreSQL   ¦
¦  (Frontend)    ¦     ¦  + Middleware ¦     ¦  + pgvector   ¦
+----------------+     +--------------+     +--------------+
                              ¦
                    +-------------------+
                    ¦  Agent/Skill Layer ¦
                    +-------------------+
                    +-------------------+
                    ¦  Retrieval Engine  ¦
                    +-------------------+
                    +-------------------+
                    ¦  Provider Router   ¦
              +-----?-----+       +----?-----+
              ¦ Anthropic  ¦       ¦  Ollama   ¦
              ¦   Claude   ¦       ¦ (Local)   ¦
              +------------+       +-----------+
```

### Technology Stack

| Layer | Technology |
|-------|-----------|
| Frontend | React + TypeScript + Vite |
| API | FastAPI + Uvicorn |
| Database | PostgreSQL 16 + pgvector |
| ORM | SQLAlchemy 2.x |
| Migrations | Alembic |
| LLM Routing | Custom Provider Abstraction |
| Configuration | pydantic-settings |
| Observability | Structured JSON Logging + X-Request-ID |

### Core Components

1. **Provider Router**
   - Implements an `LLMProvider` interface.
   - Hot-swaps between `AnthropicProvider` and `OllamaProvider` via the `MODEL_PROVIDER` environment variable.
2. **Retrieval Engine (RAG)**
   - Uses `pgvector` and `<=>` (cosine distance) for similarity search against embedded podcast transcripts.
   - Forces strict thresholds to prevent hallucination when evidence is weak.
3. **Agent / Skill Layer**
   - **GroundedConversationalAgent**: Handles Q&A using retrieved context.
   - **Ship30Skill**: Orchestrates 1,250-word essay generation with word-count and citation validation logic (max 2 attempts).
   - **ArtifactSkill**: Handles structured Markdown or HTML artifact generation.
4. **Artifact Viewer & Security Boundary**
   - HTML artifacts are rendered using a sandboxed `<iframe>` (`sandbox=""`) combined with a restrictive Content Security Policy (`CSP`) to entirely prevent Cross-Site Scripting (XSS).
5. **Observability & Hardening**
   - Middleware handles request correlation via `X-Request-ID`.
   - Structured JSON logging emits high-value signals (latency, groundedness, word counts, citations) for evaluation and monitoring without spamming raw prompts/responses.
