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

Follow this path to get the application running locally for evaluation.

### 1. Configure Environment
Create a `.env` file based on `.env.example`:
```bash
cp .env.example .env
```
Ensure you have Docker and Docker Compose installed.

### 2. Start Services
```bash
docker compose up --build -d
```

### 3. Verify Health
Wait for the containers to initialize, then verify backend health:
```bash
curl http://localhost:8000/health/ready
```

### 4. Ingest Sample Transcripts
Populate the knowledge base with the included JSON transcript fixture. Run this from the repository root (requires local Python environment):
```bash
$env:POSTGRES_HOST="localhost"
backend\.venv\Scripts\python ingestion\ingest.py --file ingestion\fixtures\sample_episode.json
```

### 5. Open Application
Navigate to the frontend in your browser:
`http://localhost:3000`

### 6. Run Tests
Run the backend tests:
```bash
docker compose exec api pytest tests/
```
Run the frontend tests (locally requires Node):
```bash
cd frontend && npm install && npm run test
```

### 7. Run Deterministic Evaluation
A deterministic evaluation harness verifies groundedness and system constraints (e.g. Ship30 word count, invalid citation rejection, session isolation). Run this from the repository root:
```bash
$env:POSTGRES_HOST="localhost"; $env:PYTHONPATH="backend"
backend\.venv\Scripts\python eval\evaluate.py
```

## What to Try First
If you have 5 minutes, try this recommended workflow:
1. Start the stack and open `http://localhost:3000`.
2. Create/open a session.
3. **Grounded Q&A**: Ask a question like *"What did Brian Chesky say about Airbnb's early growth?"*
4. Inspect the resulting citation and source linkage.
5. **Multi-turn**: Ask a follow-up referring to the previous answer.
6. **Ship30**: Ask the assistant to turn the insight into a Ship 30 for 30 essay. Observe the 1,250-word length and grounded citations.
7. **Artifact**: Ask the assistant to generate a Markdown checklist or an HTML layout.
8. **Artifact Viewer**: Click the generated artifact to see it rendered safely.
9. **Insufficient Evidence**: Try an unsupported question like *"What are the specs of the SpaceX Starship?"* and observe the safe fallback response without fabricated citations.

## Provider Switching
You can switch providers instantly without changing code by updating your `.env` or setting the environment variable before startup:
```bash
MODEL_PROVIDER=anthropic docker compose up -d
# or
MODEL_PROVIDER=ollama docker compose up -d
```
*(If using Ollama, ensure the model is pulled locally: `ollama run llama3.1:8b`)*

## Repository Structure
- `backend/`: FastAPI application, Agent orchestration, Skills, RAG logic, and API routes.
- `frontend/`: React + Vite application and UI components.
- `docs/`: Product Requirements (PRD), Architecture, and Design documentation.
- `eval/`: Deterministic evaluation harness and test cases.
- `ingestion/`: Sample transcript fixture and ingestion scripts.
- `agent-transcripts/`: Historical execution logs and phase summaries.

## Security
- **Untrusted HTML**: Generated HTML artifacts are treated as hostile.
- **Sandboxed Iframe**: HTML is rendered in `<iframe sandbox="" srcDoc="...">`, explicitly disabling scripts, forms, popups, and top-navigation.
- **CSP**: A restrictive Content-Security-Policy is injected into all HTML artifacts.
- **No dangerouslySetInnerHTML**: Prohibited across the entire codebase.

## Known Limitations
- **Static Corpus**: The application relies on a static JSON fixture; it does not crawl new episodes automatically.
- **No Authentication**: Sessions are persistent via UUIDs but there is no user login/auth layer.
- **Local Ollama Quality**: When running `llama3.1:8b` locally, generation latency and formatting adherence may differ from Anthropic Claude models.
- **English Focus**: The system is tuned and validated strictly for English content.
