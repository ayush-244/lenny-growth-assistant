# Architecture

## The Lenny Growth Assistant

### High-Level Architecture

```text
┌─────────────┐     ┌──────────────┐     ┌──────────────┐
│   Frontend   │────▶│  FastAPI API  │────▶│  PostgreSQL   │
│  (Phase 3+)  │     │   + Agents   │     │  + pgvector   │
└─────────────┘     └──────────────┘     └──────────────┘
                           │
                    ┌──────┴──────┐
                    │             │
              ┌─────▼─────┐ ┌────▼─────┐
              │  Anthropic │ │  Ollama   │
              │   Claude   │ │  (Local)  │
              └───────────┘ └──────────┘
```

### Technology Stack

| Layer | Technology |
|-------|-----------|
| API | FastAPI + Uvicorn |
| Agent SDK | Anthropic Claude Agent SDK |
| Database | PostgreSQL 16 + pgvector |
| ORM | SQLAlchemy 2.x |
| Migrations | Alembic |
| Configuration | pydantic-settings |
| Containerization | Docker + Docker Compose |

### Key Design Decisions

1. **Synchronous SQLAlchemy** — Simpler foundation; async can be layered on if needed
2. **psycopg3 driver** — Modern PostgreSQL adapter with connection pooling
3. **pgvector** — Native PostgreSQL vector similarity search for RAG
4. **Alembic for migrations** — No `create_all()` at startup; schema managed declaratively
5. **Environment-based configuration** — All secrets and settings via environment variables

### Status

This document will be expanded as the architecture evolves across phases.

*Phase 1: Foundation established with FastAPI, PostgreSQL, SQLAlchemy, and Alembic.*
