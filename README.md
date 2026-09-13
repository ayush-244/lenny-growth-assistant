# The Lenny Growth Assistant

The Lenny Growth Assistant is a conversational AI designed to help product managers, founders, and growth practitioners navigate the knowledge base of Lenny Rachitsky's newsletter and podcast.

## Product Problem
Professionals often struggle to find specific, actionable insights buried in hundreds of podcast episodes and newsletter posts. The Lenny Growth Assistant solves this by retrieving exact factual evidence from transcripts and summarizing it into grounded, actionable answers.

## Core Workflow
1. **Question**: User asks a product/growth question.
2. **Retrieval**: System retrieves relevant transcript chunks using pgvector cosine similarity.
3. **Grounded Answer**: The LLM synthesizes an answer using *only* the retrieved evidence.
4. **Citation**: Exact episode/source citations are provided inline.
5. **Ship30/Artifact**: Users can optionally generate a Ship 30 for 30 essay or Markdown/HTML artifacts based directly on the retrieved evidence.

## Features
- **Grounded Q&A**: Refuses to answer if evidence is insufficient (no hallucinations).
- **Citations**: Direct links to the underlying episodes.
- **Persistent Sessions**: Chat history is saved to a PostgreSQL database.
- **Ship30**: Generate 1,250-word essays grounded in transcript facts.
- **Artifacts**: Generate structured Markdown or interactive HTML/CSS layouts.
- **Safe HTML Viewer**: HTML artifacts are strictly sandboxed in an iframe with a restrictive CSP.
- **Provider Switching**: Seamlessly switch between Anthropic (Claude) and Ollama (local Llama 3.1) via environment variables.

## Architecture
- **Frontend**: React + Vite + TypeScript.
- **Backend**: FastAPI + Python 3.12.
- **Agent/Skill Layer**: Custom orchestration for Retrieval, Ship30, and Artifact generation.
- **Retrieval + Model Provider**: Custom Abstractions for Anthropic and Ollama.
- **Database**: PostgreSQL with pgvector for embeddings and ORM state (users, sessions, messages, artifacts).

## Quick Start
The simplest way to run the application is via Docker Compose:
```bash
docker compose up --build -d
```
The API will be available at `http://localhost:8000` and the frontend at `http://localhost:3000`.

## Environment Variables
Create a `.env` file based on `.env.example`:
- `MODEL_PROVIDER`: Set to `ollama` or `anthropic`.
- `ANTHROPIC_API_KEY`: Required if using Anthropic.
- `OLLAMA_BASE_URL` & `OLLAMA_MODEL`: Settings for local Ollama usage.
- `EMBEDDING_PROVIDER` & `EMBEDDING_MODEL`: Provider for pgvector embeddings.
- `POSTGRES_*`: Database credentials.

## Knowledge Ingestion
To populate the knowledge base with the included JSON transcript fixture:
```bash
docker compose exec api python -m scripts.ingest --file ./ingestion/sample_transcripts.json
```

## Provider Switching
You can switch providers instantly without changing code by updating your `.env` or setting the environment variable before startup:
```bash
MODEL_PROVIDER=anthropic docker compose up -d
# or
MODEL_PROVIDER=ollama docker compose up -d
```
*(If using Ollama, ensure the model is pulled: `ollama run llama3.1:8b`)*

## Testing
Run the backend tests (requires local PostgreSQL):
```bash
$env:POSTGRES_HOST="localhost"; backend\.venv\Scripts\pytest backend\tests
```
Run the frontend tests:
```bash
cd frontend && npx vitest run
```

## Evaluation
A deterministic evaluation harness is provided to verify groundedness and system constraints (e.g. Ship30 word count, invalid citation rejection, session isolation).
Run it with:
```bash
python eval/evaluate.py
```

## Security
- **Untrusted HTML**: Generated HTML artifacts are treated as hostile.
- **Sandboxed Iframe**: HTML is rendered in `<iframe sandbox="" srcDoc="...">`, explicitly disabling scripts, forms, popups, and top-navigation.
- **CSP**: A restrictive Content-Security-Policy is injected into all HTML artifacts.
- **No dangerouslySetInnerHTML**: Prohibited across the entire codebase.

## Known Limitations
- **Static Corpus**: The application relies on a static JSON fixture; it does not crawl new episodes automatically.
- **No Authentication**: Sessions are persistent via UUIDs but there is no user login/auth layer.
- **Local Ollama Quality**: When running `llama3.1:8b` locally, generation latency and formatting adherence may differ from Claude 3.5 Sonnet.
- **English Focus**: The system is tuned and validated strictly for English content.
