# The Lenny Growth Assistant

An AI conversational assistant powered by Lenny's Podcast and Newsletter insights. Built with FastAPI, PostgreSQL (pgvector), and the Anthropic Claude Agent SDK.

## Current Status

**Phase 1 — Project Foundation** ✅

The application foundation is in place:
- FastAPI backend with health endpoint
- PostgreSQL with pgvector support
- Docker Compose orchestration
- SQLAlchemy and Alembic foundation
- Configuration via environment variables

> **Note:** RAG, agents, transcript ingestion, artifacts, and frontend are not yet implemented. These will be built in subsequent phases.

## Architecture

| Component | Technology |
|-----------|-----------|
| Backend API | FastAPI + Uvicorn |
| Database | PostgreSQL 16 with pgvector |
| ORM | SQLAlchemy 2.x |
| Migrations | Alembic |
| Configuration | pydantic-settings |
| Agent Layer | Anthropic Claude Agent SDK *(Phase 2+)* |
| Frontend | TBD *(Phase 3+)* |

## Prerequisites

- [Docker](https://www.docker.com/) and Docker Compose
- Git

For local development without Docker:
- Python 3.12+
- PostgreSQL 16 with pgvector extension

## Quick Start

```bash
# Clone the repository
git clone <repository-url>
cd lenny-growth-assistant

# Create environment file
cp .env.example .env

# Start all services
docker compose up --build
```

The application will be available at:
- **Frontend UI:** http://localhost:3000/
- **Backend API:** http://localhost:8000/
- **API Health:** http://localhost:8000/health

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `APP_ENV` | `development` | Application environment |
| `POSTGRES_HOST` | `db` | PostgreSQL host |
| `POSTGRES_PORT` | `5432` | PostgreSQL port |
| `POSTGRES_DB` | `lenny` | Database name |
| `POSTGRES_USER` | `lenny` | Database user |
| `POSTGRES_PASSWORD` | `lenny` | Database password |
| `MODEL_PROVIDER` | `ollama` | LLM provider (`ollama` or `anthropic`) |
| `OLLAMA_BASE_URL` | `http://host.docker.internal:11434` | Ollama API base URL |
| `OLLAMA_MODEL` | `llama3.1:8b` | Ollama model name |
| `ANTHROPIC_API_KEY` | *(empty)* | Anthropic API key |
| `EMBEDDING_PROVIDER` | `local` | Embedding provider |
| `EMBEDDING_MODEL` | *(empty)* | Embedding model name |
| `EMBEDDING_DIMENSION` | *(empty)* | Embedding vector dimension |
| `VITE_API_URL` | `http://localhost:8000` | Frontend API Base URL (defaults to localhost:8000) |

## Running Tests

```bash
cd backend
pip install -r requirements.txt
pytest tests/ -v

cd frontend
npm install
npx vitest run
```

## Project Structure

```text
lenny-growth-assistant/
├── backend/
│   ├── app/
│   │   ├── api/           # API routes
│   │   ├── core/          # Configuration
│   │   ├── db/            # Database foundation
│   │   ├── agents/        # Agent layer
│   │   ├── rag/           # RAG pipeline
│   │   ├── llm/           # LLM providers
│   │   ├── schemas/       # Pydantic schemas
│   │   ├── services/      # Business logic
│   │   └── main.py        # FastAPI application
│   ├── alembic/           # Database migrations
│   ├── tests/             # Test suite
│   ├── Dockerfile
│   └── requirements.txt
├── frontend/              # Frontend React application
├── ingestion/             # Transcript ingestion
├── docs/                  # Documentation
├── agent-transcripts/     # Agent implementation transcripts
├── scripts/               # Utility scripts
├── docker-compose.yml
├── .env.example
└── README.md
```

## Development Roadmap

- [x] **Phase 1** — Project Foundation
- [x] **Phase 2** — Database Schema, RAG Pipeline, Agent Layer
- [x] **Phase 3** — Grounded Conversational Core (LLM Providers)
- [x] **Phase 4** — Frontend Core Chat Experience
- [ ] **Phase 5** — TBD
