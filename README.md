# 🚀 The Lenny Growth Assistant

The **Lenny Growth Assistant** is a conversational AI designed to help product managers, founders, and growth practitioners navigate the knowledge base of Lenny Rachitsky's newsletter and podcast.

---

## 🎯 Product Problem

Professionals often struggle to find specific, actionable insights buried in hundreds of podcast episodes and newsletter posts. The Lenny Growth Assistant solves this by retrieving relevant factual evidence from transcripts and summarizing it into grounded, actionable answers.

---

## 🔄 Core Workflow

1. ❓ **Question**: User asks a product/growth question.

2. 🔍 **Retrieval**: System retrieves relevant transcript chunks using pgvector cosine similarity.

3. 🤖 **Grounded Answer**: The LLM synthesizes an answer using only the retrieved evidence.

4. 🔗 **Citation**: Exact episode/source citations are provided inline.

5. 📝 **Ship30/Artifact**: Users can optionally generate a Ship 30 for 30 essay or Markdown/HTML artifacts based directly on the retrieved evidence.

---

## ✨ Features

- **Grounded Q&A**: Refuses to answer if evidence is insufficient instead of fabricating unsupported claims.

- **Citations**: Responses include source metadata and transcript timestamps where available.

- **Persistent Sessions**: Chat history is saved to a PostgreSQL database.

- **Ship30**: Generate approximately 1,250-word essays grounded in transcript evidence.

- **Artifacts**: Generate structured Markdown or interactive HTML/CSS layouts.

- **Safe HTML Viewer**: HTML artifacts are sandboxed in an iframe with a restrictive CSP.

- **Provider Switching**: Switch between Anthropic and Ollama at the session level without changing application code.

---

## 🏗️ Architecture

- **Frontend**: React + Vite + TypeScript.

- **Backend**: FastAPI + Python 3.12.

- **Agent/Skill Layer**: Custom orchestration for retrieval, conversational Q&A, Ship30, and artifact generation.

- **Retrieval + Model Provider**: Custom abstractions for pgvector retrieval and Anthropic/Ollama model providers.

- **Database**: PostgreSQL with pgvector for transcript embeddings and application state including sessions, messages, transcripts, chunks, and artifacts.

---

## 🚀 Quick Start

Follow this path to get the application running locally for evaluation.

### 1️⃣ Configure Environment

Create a `.env` file based on `.env.example`:

```bash
cp .env.example .env
```

Ensure you have Docker and Docker Compose installed.

### 2️⃣ Start Services

```bash
docker compose up --build -d
```

### 3️⃣ Verify Health

Wait for the containers to initialize, then verify backend readiness:

```bash
curl http://localhost:8000/health/ready
```

Expected response:

```json
{
  "status": "ready",
  "database": "ok"
}
```

### 4️⃣ Ingest Sample Transcripts

Populate the knowledge base with the included JSON transcript fixture.

Run this from the repository root using the local Python environment:

```powershell
$env:POSTGRES_HOST="localhost"

backend\.venv\Scripts\python ingestion\ingest.py --file ingestion\fixtures\sample_episode.json
```

The ingestion pipeline creates transcript chunks and their vector embeddings in PostgreSQL.

### 5️⃣ Open Application

Navigate to the frontend in your browser:

```text
http://localhost:3000
```

### 6️⃣ Run Tests

Run the backend tests:

```bash
docker compose exec api pytest tests/
```

Build the frontend:

```bash
cd frontend
npm install
npm run build
```

### 7️⃣ Run Deterministic Evaluation

A deterministic evaluation harness verifies groundedness and system constraints including Ship30 word count, invalid citation rejection, artifact generation, and session isolation.

Run this from the repository root:

```powershell
$env:POSTGRES_HOST="localhost"
$env:PYTHONPATH="backend"

backend\.venv\Scripts\python eval\evaluate.py
```

---

## 🎮 What to Try First

If you have 5 minutes, try this recommended workflow:

1. Start the stack and open `http://localhost:3000`.

2. Create/open a session.

3. 💬 **Grounded Q&A**: Ask a question such as:

   > "What did Brian Chesky say about Airbnb's early growth?"

4. 🔎 Inspect the resulting citation and source linkage.

5. 💬 **Multi-turn**: Ask a follow-up referring to the previous answer.

6. 📝 **Ship30**: Ask the assistant to turn the insight into a Ship 30 for 30 essay. Observe the approximately 1,250-word output and grounded citations.

7. 🎨 **Artifact**: Ask the assistant to generate a Markdown checklist or an HTML layout.

8. 🖼️ **Artifact Viewer**: Open the generated artifact to see it rendered safely.

9. 🛡️ **Insufficient Evidence**: Try an unsupported question such as:

   > "What are the specs of the SpaceX Starship?"

   The assistant should return an insufficient-evidence response rather than fabricate an answer or citation.

---

## 🔌 Provider Switching

New conversations use `MODEL_PROVIDER` as their default provider.

The in-app model selector stores the provider choice on each conversation, so switching one session does not affect another or require an application restart.

### Ollama

**Ollama** is the local demo provider.

The validated local model configuration is:

```text
OLLAMA_MODEL=llama3.2:3b
```

The embedding model is:

```text
EMBEDDING_MODEL=nomic-embed-text
```

Make sure the configured Ollama models are available locally before using the local provider.

### Anthropic

**Anthropic** is the optional cloud provider and requires:

```text
ANTHROPIC_API_KEY
```

Never commit API credentials or other secrets to the repository.

Provider selection is session-scoped, so changing the provider in one conversation does not change the provider of another conversation.

---

## 📂 Repository Structure

```text
backend/
├── app/
│   ├── agents/          # Agent orchestration and grounding
│   ├── api/              # FastAPI routes
│   ├── core/             # Configuration and application settings
│   ├── db/               # Database models and persistence
│   ├── llm/              # LLM provider abstractions
│   ├── rag/              # Retrieval logic
│   └── skills/           # Ship30 and Artifact skills
└── tests/                # Backend automated tests

frontend/
├── src/
│   ├── components/       # UI components
│   └── ...               # React application
└── ...

docs/
├── PRD.md
├── architecture.md
└── design.md

eval/
├── questions.json
└── evaluate.py

ingestion/
├── ingest.py
└── fixtures/

agent-transcripts/
└── Historical execution logs and phase summaries
```

---

## 🔒 Security

* ☢️ **Untrusted HTML**: Generated HTML artifacts are treated as untrusted content.

* 📦 **Sandboxed Iframe**: HTML is rendered using:

```html
<iframe sandbox="" srcDoc="...">
```

The empty sandbox attribute prevents scripts and other privileged browser capabilities from being granted to the generated document.

* 🛡️ **CSP**: A restrictive Content Security Policy is injected into HTML artifacts.

* 🚫 **No `dangerouslySetInnerHTML`**: Direct React DOM injection is prohibited across the codebase.

* 🚫 **No Dynamic Code Execution**: Generated artifacts are not executed through `eval` or `new Function`.

* 🔐 **Session Isolation**: Sessions, messages, and artifacts are scoped to their associated session IDs.

---

## 📊 Grounding & Evaluation

The application is designed around a simple principle:

> **Grounded over impressive.**

For supported questions:

1. The user query is embedded.
2. Relevant transcript chunks are retrieved from pgvector.
3. Retrieved chunks are supplied to the agent as explicit evidence.
4. The model must reference retrieved evidence using the grounding reference mechanism.
5. Returned references are validated against the actual retrieved chunks.
6. Valid references are mapped back to transcript metadata.
7. If valid evidence cannot support the answer, the assistant returns an insufficient-evidence response.

The deterministic evaluation suite checks:

* Grounded answers
* Insufficient-evidence behavior
* Citation validation
* Ship30 generation
* Ship30 word-count constraints
* Artifact generation
* Session isolation

---

## 📝 Ship30

The dedicated Ship30 skill transforms grounded insights into long-form essays.

The output is validated against:

* Target length: approximately 1,250 words
* Accepted range: 1,100–1,400 words
* Grounding against retrieved transcript evidence
* Citation validity
* Maximum of two generation attempts

If generated content fails the required validation checks, the skill can retry generation before returning a safe failure.

---

## 🎨 Artifacts

The assistant can generate:

* Markdown artifacts
* HTML/CSS artifacts

Generated artifacts are persisted against the current session and displayed inside the application's Artifact Viewer.

HTML is treated as untrusted content and rendered inside an isolated sandboxed iframe with a restrictive Content Security Policy.

---

## 🏥 Health & Operations

The backend exposes health endpoints for operational checks.

### Health

```text
GET /health
```

Returns the basic application health status.

### Readiness

```text
GET /health/ready
```

Checks application readiness including database connectivity.

The application also uses structured logging with request/session/provider metadata to make retrieval, model calls, artifact generation, and failures easier to diagnose.

---

## ⚠️ Known Limitations

* 📄 **Static Corpus**: The application relies on a static JSON fixture for the evaluation corpus and does not automatically crawl or synchronize new episodes.

* 👤 **No Authentication**: Sessions are persistent via UUIDs, but there is no user login or authentication layer because the evaluation application is single-tenant.

* 🐢 **Local Ollama Quality**: When running `llama3.2:3b` locally, generation latency and formatting adherence may differ from Anthropic Claude models.

* 💻 **Local Hardware Dependency**: Ollama performance depends on the available CPU/GPU and system memory.

* 🌐 **English Focus**: The system is tuned and validated for English content.

* 🔄 **Manual Knowledge Refresh**: New transcript content requires running the ingestion pipeline rather than an automated synchronization process.

---

## 🛠️ Troubleshooting

### Ollama unavailable

Verify that Ollama is running and that the configured model is available:

```text
llama3.2:3b
```

Also verify the configured `OLLAMA_BASE_URL` in `.env`.

### Database not ready

Check container status:

```bash
docker compose ps
```

The database should report as healthy before running ingestion or evaluation.

### Backend readiness check fails

Run:

```bash
docker compose logs api
```

and:

```bash
docker compose logs db
```

Check that PostgreSQL is running and that the configured database environment variables match the Docker Compose configuration.

### Knowledge base is empty

Run the ingestion command again:

```powershell
$env:POSTGRES_HOST="localhost"

backend\.venv\Scripts\python ingestion\ingest.py --file ingestion\fixtures\sample_episode.json
```

### Frontend build fails

From the frontend directory:

```bash
npm install
npm run build
```

If dependencies are stale, remove `node_modules` and reinstall before rebuilding.

---

## 📚 Documentation

Additional project documentation is available in the `docs/` directory:

* `docs/PRD.md` — product requirements, scope, metrics, risks, and acceptance criteria.
* `docs/architecture.md` — system architecture, database schema, API contracts, retrieval flow, agent routing, security, and deployment topology.
* `docs/design.md` — UI/UX principles, information architecture, interaction states, responsive behavior, accessibility, and design decisions.

Agent execution history and important corrections are documented in:

```text
agent-transcripts/
```

---

## 🏁 Evaluation Checklist

Before submitting, verify:

* [ ] Docker Compose starts successfully.
* [ ] `/health` returns a healthy response.
* [ ] `/health/ready` reports database readiness.
* [ ] Sample transcript ingestion succeeds.
* [ ] Grounded questions return valid citations.
* [ ] Unsupported questions return insufficient evidence.
* [ ] Session histories remain isolated.
* [ ] Ollama provider works locally.
* [ ] Anthropic provider can be configured without code changes.
* [ ] Ship30 output satisfies validation requirements.
* [ ] Markdown artifacts render correctly.
* [ ] HTML artifacts render inside the sandboxed viewer.
* [ ] Backend tests pass.
* [ ] Frontend production build passes.
* [ ] Deterministic evaluation passes.
* [ ] No secrets are committed.
* [ ] README and architecture/design documentation match the implementation.

---

## 🎯 Product Principle

The Lenny Growth Assistant is built around one core principle:

> **When the system is uncertain, it should be transparent rather than impressive.**

The goal is not simply to generate convincing answers.

The goal is to help users move from:

**Question → Evidence → Insight → Actionable Artifact**
