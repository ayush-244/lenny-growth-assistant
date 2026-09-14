# 🚀 Product Requirements Document

## 🎙️ The Lenny Growth Assistant

---

### 🌟 Overview

The **Lenny Growth Assistant** is a conversational AI designed to help product managers, founders, and growth practitioners navigate the knowledge base of Lenny Rachitsky's newsletter and podcast.

The product turns a large transcript corpus into a grounded, searchable assistant that can answer product and growth questions, cite the underlying evidence, and transform useful insights into reusable written content and artifacts.

---

### 🎯 Forward Deployment Brief

#### 👥 User and Problem

The primary users are **product managers, founders, and growth practitioners** who need to make product or growth decisions quickly.

Their job is to find a specific, actionable insight from Lenny's podcast and newsletter knowledge **without** manually searching hundreds of episodes or re-listening to long-form content.

> The assistant removes the manual search and synthesis work while preserving source traceability so users can understand where an answer came from.

#### 🛠️ Job-To-Be-Done (JTBD)

> *"When I am stuck on a growth or product problem, I want to quickly query Lenny's insights so that I can apply proven tactics to my work immediately."*

#### 🛑 Pain Points

- 📚 High volume of unstructured audio and text content.
- 🧠 Hard to remember which episode contained a specific insight.
- ⏳ Time-consuming manual searching across transcripts and episodes.
- 🤖 Risk of AI hallucinations when asking general-purpose LLMs about niche advice.
- 📝 Difficulty turning a useful insight into a reusable document or artifact.

---

### 📏 Scope & Acceptance Criteria

1. **Grounded Q&A**: Must answer questions using *only* retrieved evidence from the knowledge base.
2. **Citations**: Must provide verifiable citations to the underlying transcript source, including episode/source metadata and timestamps where available.
3. **Artifact Generation**: Must generate Markdown documents and HTML/CSS layouts that can be viewed inside the application.
4. **Ship30 Skill**: Must generate approximately 1,250-word essays within the validated 1,100–1,400 word range and keep claims grounded in retrieved evidence.
5. **Session Persistence**: Must retain conversation context, messages, citations, and session metadata in PostgreSQL.
6. **Provider Agnostic**: Must support switching between Anthropic and local Ollama inference without changing application code.
7. **Security**: Generated HTML must be treated as untrusted content and rendered inside a sandboxed iframe with a restrictive Content Security Policy.
8. **Insufficient Evidence**: Must explicitly acknowledge when the knowledge base does not contain enough evidence to answer a question rather than fabricating an answer.
9. **Session Isolation**: Conversations and artifacts from one session must not be exposed to another session.

---

### 🤔 Assumptions

- 🗄️ The evaluation transcript corpus is treated as a relatively static dataset and can be refreshed manually through the ingestion pipeline.
- 🎓 Users have basic familiarity with Lenny's content style and product/growth terminology.
- 💻 Local execution relies on the user having sufficient resources to run Ollama and the selected local model.
- 🐢 The local Ollama model may produce lower-quality or slower responses than a cloud model, but must still provide coherent and grounded answers for the evaluation workflow.
- 🐘 PostgreSQL with pgvector is used as the system of record and vector retrieval layer to keep the deployment simple and reproducible.
- 👤 The application is single-tenant for the evaluation and does not require authentication.
- 🇺🇸 The application is English-focused.
- 🛡️ Generated HTML is considered untrusted and must never be inserted directly into the parent application's DOM.

---

### 📦 Scope Choices

#### ✅ Included

- Grounded conversational Q&A over the Lenny transcript knowledge base.
- Persistent and independently scoped chat sessions.
- Source citations with transcript and timestamp metadata.
- Dedicated Ship30 for 30 content generation.
- Markdown and HTML/CSS artifact generation.
- In-app Artifact Viewer.
- Anthropic cloud inference and local Ollama inference.
- PostgreSQL and pgvector persistence/retrieval.
- Structured logging and health/readiness endpoints.
- Docker Compose deployment and evaluator documentation.

#### ❌ Intentionally Excluded

- **Authentication and user permissions** — excluded because the take-home focuses on the grounded assistant workflow rather than account management.
- **Automatic transcript crawling or synchronization** — excluded to keep the evaluation corpus deterministic and avoid introducing external crawling dependencies. Transcript refresh is handled through the ingestion pipeline.
- **Enterprise multi-tenancy** — excluded because the evaluation is designed as a single-tenant application.
- **Voice and mobile-native applications** — excluded because they do not materially improve the core transcript search, grounded Q&A, writing, and artifact workflow.
- **Real-time collaboration** — excluded to keep the implementation focused on the primary individual research workflow.

---

### 📊 Metrics & Evaluation

#### 1️⃣ Groundedness Rate

> **Target: ≥90% of supported assistant answers should contain at least one valid citation to a retrieved transcript chunk.**

Each conversational turn is classified as `grounded`, `insufficient_context`, or `error`. Citation validation ensures that returned citations correspond to evidence actually retrieved for that request.

#### 2️⃣ Artifact Generation Latency

> **Target: Typical local artifact requests should complete in under 15 seconds on the demo machine.**

Retrieval and model latency are logged so performance can be diagnosed and evaluated.

#### 3️⃣ Evaluation Reliability

> **Target: 100% of the deterministic evaluation suite should pass before submission.**

The evaluation suite covers grounded answers, insufficient evidence, Ship30 generation, artifact generation, citation validation, and session isolation.

#### 4️⃣ Ship30 Validation

Ship30 outputs are validated against:

- Target word count: approximately 1,250 words.
- Accepted range: 1,100–1,400 words.
- Citation validity.
- Grounding against retrieved transcript evidence.
- Maximum of two generation attempts.

---

### ⚠️ Risks & Trade-offs

| Risk | Impact | Mitigation |
|---|---|---|
| **Hallucination** | The model may generate claims unsupported by Lenny's transcripts. | Retrieval-grounded generation, strict citation validation, and explicit insufficient-evidence fallback. |
| **Latency** | Local model generation may be slower than cloud inference. | Use a machine-appropriate Ollama model, configure generation limits, and log retrieval/model latency. |
| **Cost** | Cloud model usage can introduce API and token costs. | Ollama is the mandatory local demo path; cloud inference remains configurable rather than required for every request. |
| **Local-model quality** | Smaller local models may produce weaker or shorter responses. | Use a model appropriate for the demo hardware, provide explicit generation limits, and validate/retry generated content where required. |
| **Data leakage** | Session or artifact data could accidentally cross user/session boundaries. | Session-scoped database queries, explicit foreign-key relationships, and automated session-isolation tests. |
| **Unsafe artifact rendering** | Generated HTML could contain scripts or browser-level attacks. | Render HTML inside a sandboxed iframe with a restrictive CSP and avoid injecting generated HTML into the parent DOM. |
| **Stale content** | The knowledge base can become outdated as new episodes are published. | Provide a repeatable manual ingestion pipeline through `ingestion/ingest.py` so the corpus can be refreshed when required. |

---

### 💎 Product Principles

1. **Grounded over impressive** — when the evidence is insufficient, the assistant should say so rather than guess.
2. **Traceable by default** — important claims should be connected to the transcript evidence that supports them.
3. **Useful output, not just answers** — insights should be convertible into reusable essays and artifacts.
4. **Simple deployment** — the system should be understandable and runnable by another engineer without unnecessary infrastructure.
5. **Safe by design** — generated content is treated as untrusted, especially when rendered as HTML.

---

### 🔄 Core User Flows

#### 🌊 Flow 1: Grounded Question Answering

1. User creates a new session.
2. User asks a product or growth question.
3. System retrieves relevant transcript chunks.
4. Agent generates an answer using the retrieved evidence.
5. Valid citations are mapped to transcript/source metadata.
6. Answer and citations are persisted to the session.
7. If evidence is insufficient, the assistant explicitly says so.

#### 📝 Flow 2: Ship30 Essay

1. User asks for a Ship30-style essay from the current conversation.
2. System retrieves relevant evidence.
3. Ship30 skill generates approximately 1,250 words.
4. Citation and word-count validation runs.
5. If validation fails, generation may be retried once.
6. Valid output is returned and persisted.

#### 🎨 Flow 3: Artifact Generation

1. User requests an artifact from the current conversation.
2. System generates Markdown or HTML/CSS.
3. Artifact is persisted against the current session.
4. Frontend displays it through the Artifact Viewer.
5. HTML is rendered in an isolated sandboxed iframe.

#### 🔌 Flow 4: Provider Switching

1. User selects Anthropic or Ollama.
2. Provider selection is saved against the current session.
3. Subsequent generation requests use that session's provider.
4. Switching sessions restores the provider associated with each session.

---

### ✅ Acceptance Criteria

The product is considered ready when:

- [x] A new user can create an independent chat session.
- [x] Questions are answered using retrieved transcript evidence.
- [x] Supported answers contain valid source citations.
- [x] Unsupported questions receive an explicit insufficient-evidence response.
- [x] Follow-up questions retain the current session context.
- [x] Ship30 generation produces a validated approximately 1,250-word essay.
- [x] Generated artifacts render inside the application.
- [x] Generated HTML cannot execute unrestricted scripts in the parent application.
- [x] Users can switch between Ollama and Anthropic without code changes.
- [x] PostgreSQL persists sessions, messages, citations, transcripts, chunks, and artifacts.
- [x] Docker Compose starts the required application services.
- [x] Health and readiness endpoints provide operational status.
- [x] Automated tests and the evaluation suite pass.
- [x] Another engineer can understand the setup and troubleshooting process from the repository documentation.

---

### 🗺️ Implementation Plan

1. Backend and PostgreSQL foundation.
2. Transcript ingestion, chunking, embeddings, and pgvector retrieval.
3. LLM provider abstraction and grounded conversational agent.
4. Core frontend and session-based chat experience.
5. Dedicated Ship30 skill with validation and retry behavior.
6. Artifact generation and secure in-app viewer.
7. Structured logging, resilience, evaluation harness, and operational documentation.
8. Final integration testing, Docker validation, and evaluator handoff.