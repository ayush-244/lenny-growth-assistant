# Phase 6: Artifact Viewer Implementation Transcript

## 1. Phase 6 Objective
Implement a secure, grounded artifact-generation capability (Markdown + HTML/CSS) with a sandboxed Artifact Viewer panel. The implementation must isolate sessions, securely render user-facing HTML, and adhere to existing architecture.

## 2. Architecture Decisions
- A dedicated `Artifact` model with a UUID primary key and `session_id` foreign key ensures clean session isolation without cluttering the `Message` table.
- HTML security relies strictly on the native browser `<iframe sandbox="">` boundary; `dangerouslySetInnerHTML` is prohibited.
- `srcDoc` is used to load HTML without external blob navigation, while a strict Content Security Policy (CSP) `<meta>` tag is injected directly into generated HTML.
- LLM abstraction leverages the existing `get_llm_provider()` layer, avoiding hardcoded client dependencies.

## 3. Backend Implementation
- **Artifact model**: SQLAlchemy `Artifact` model mapping to `artifacts` table. Contains fields for type, content, grounded status, and a cascading `session_id` relationship.
- **Alembic migration**: `0003_artifacts.py` manages table creation and removal.
- **ArtifactSkill**: The generation engine (`backend/app/skills/artifact.py`). It enforces context limits, validates the requested artifact type, pulls from the retriever, prompts the LLM, and explicitly strips malformed markdown code-block wrappers before injecting the CSP meta tag.
- **ArtifactService**: Provides `create_artifact`, `list_artifacts`, and `get_artifact` with built-in session validation.
- **API routes**: `/sessions/{id}/artifacts` (GET/POST) and `/sessions/{id}/artifacts/{artifact_id}` endpoints added to `backend/app/api/sessions.py`.

## 4. Frontend Implementation
- **ArtifactViewer**: Conditionally renders the artifact. HTML uses a strict iframe. Markdown uses `ReactMarkdown`.
- **ArtifactPanel**: Contains the loading and error states, the artifact title/type badge, and a close button.
- **Composer controls**: `Composer.tsx` expanded to include explicit markdown (Layout icon) and HTML (Code icon) artifact creation buttons alongside standard messaging.
- **Application state**: `App.tsx` manages `activeArtifact`, loading, and error states, properly resetting them when the active session changes.

## 5. Artifact Types
- **Markdown**: Styled structured text content.
- **HTML/CSS**: Standalone web documents with inline styles. Scripts are strictly banned.

## 6. Grounding Approach
The implementation relies on the same robust `Retriever` used in Phase 5. Artifact generation checks if evidence is insufficient (`is_insufficient_evidence` and chunk count). When sufficient, the LLM is prompted strictly against the retrieved chunk context to ensure claims are factual to Lenny's content.

## 7. Security Model
- **Untrusted Input**: All generated HTML is considered hostile.
- **Iframe**: The boundary mechanism.
- **sandbox=""**: Enforces the strictest possible restrictions—no scripts, no same-origin DOM access, no form submission, no popups.
- **srcDoc**: Provides the document directly to the iframe memory, preventing blob URL leakage.
- **CSP**: The `ArtifactSkill` explicitly prepends `<meta http-equiv="Content-Security-Policy" content="default-src 'none'; style-src 'unsafe-inline'; img-src data:; font-src data:;">` to all HTML artifacts to prevent external resource loading.
- **No dangerouslySetInnerHTML**: Zero occurrences in the codebase.
- **No scripts**: Prohibited by the sandbox.

## 8. Session Isolation
Isolation is enforced across both backend (ORM WHERE clauses strictly filtering by `session_id`) and frontend (resetting active artifact states during session transitions).

## 9. Tests and Verification
- **Backend**: 101/101 pytest cases passed (testing generation, validation, isolation, CSP injection, stripping logic).
- **Frontend**: 5/5 Vitest cases passed (including verifying that `sandbox=""` and `srcDoc` are strictly set).
- **Production Build**: Successfully compiled (`npm run build`).
- **Docker Compose**: Containerized services start up cleanly (`docker compose up --build -d`).

## 10. Known Limitations
- The Content Security Policy allows inline styles but heavily restricts external CSS. Artifacts requiring complex external styling libraries (like Tailwind via CDN) will not render.
- **Manual QA**: Manual browser QA was NOT performed during the automated audit verification cycle, though comprehensive integration tests have passed.

## 11. Commit Information
- Codebase updated on commit `9042db0`.
