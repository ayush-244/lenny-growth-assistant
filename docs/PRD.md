# Product Requirements Document

## The Lenny Growth Assistant

### Overview
The Lenny Growth Assistant is a conversational AI designed to help product managers, founders, and growth practitioners navigate the knowledge base of Lenny Rachitsky's newsletter and podcast.

### Persona
- **Product Managers & Founders**: Busy professionals seeking actionable growth, product, and leadership advice without wanting to listen to 100+ hours of podcast audio or search through hundreds of newsletter archives.

### Job-To-Be-Done (JTBD)
When I am stuck on a growth or product problem, I want to quickly query Lenny's insights so that I can apply proven tactics to my work immediately.

### Pain Points
- High volume of unstructured audio/text content.
- Hard to remember which episode contained a specific insight.
- Risk of AI hallucinations when asking general purpose LLMs about niche advice.

### Scope & Acceptance Criteria
1. **Grounded Q&A**: Must answer questions using *only* retrieved evidence.
2. **Citations**: Must provide verifiable citations to episodes/newsletters.
3. **Artifact Generation**: Must generate visual HTML/CSS layouts and Markdown checklists.
4. **Ship30 Skill**: Must generate 1,100–1,400 word essays strictly grounded in facts.
5. **Session Persistence**: Must retain conversation context in a database.
6. **Provider Agnostic**: Must seamlessly swap between Anthropic and local Ollama inference.
7. **Security**: Generated HTML must be strictly sandboxed (no scripts, restricted origin).

### Assumptions
- Users have basic familiarity with Lenny's content style.
- Local execution relies on the user having sufficient RAM/GPU for Ollama if chosen.

### Metrics & Evaluation
- **Groundedness**: Ratio of grounded answers vs insufficient context/errors.
- **Latency**: Retrieval and total LLM response time.
- **Ship30 Validation**: Word count and citation adherence.

### Risks
- **Hallucinations**: Mitigated by strict retrieval checking and refusing to answer if evidence is insufficient.
- **Security (XSS)**: Mitigated by locking down Artifact Viewer iframes with `sandbox=""` and `CSP`.
- **Stale Content**: Mitigated by allowing future transcript ingestion via `scripts/ingest.py`.
