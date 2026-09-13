# Demo Script

This script outlines the recommended 2-3 minute evaluator flow for demonstrating the Lenny Growth Assistant, fulfilling the assignment's demo video requirements.

**Requirements:**
- Keep it within 2-3 minutes.
- Include presenter's face/camera.
- Speak clearly about product value.

### 0:00–0:20 — Introduction
*(Show face/camera)*
"Hi, I'm [Your Name]. This is the Lenny Growth Assistant. Professionals often struggle to find specific, actionable insights buried in hundreds of podcast episodes. This product solves that by retrieving exact factual evidence from Lenny's transcripts and summarizing it into grounded, actionable answers."

### 0:20–0:55 — Grounded Q&A
*(Share screen: Lenny Growth Assistant UI)*
- Open the application and create a new session.
- Type: *"What did Brian Chesky say about Airbnb's early growth?"*
- Point out the response quality.
- Click on the inline citation. Show the source episode and timestamp linking back to the exact evidence used by the model.
- "The assistant relies solely on retrieved facts via a RAG pipeline."

### 0:55–1:15 — Follow-up (Multi-Turn)
- Type: *"What were the specific metrics he mentioned?"*
- Show that the assistant uses the conversational context to understand "he" refers to Brian Chesky and the topic is Airbnb's early growth.

### 1:15–1:45 — Ship 30 for 30
- Click the "Ship30" button or type: *"Turn those insights into a Ship 30 for 30 essay."*
- Highlight the output: "The backend uses a dedicated skill to generate an essay that strictly hits a 1,100 to 1,400 word count target, includes a hook, and retains all citations. It features a retry loop that validates the citations before returning the result."

### 1:45–2:15 — Artifact Generation & Viewer
- Type: *"Create an HTML checklist of those growth tactics."*
- When the artifact is generated, click to open the Artifact Viewer.
- Explain: "Generated code can be dangerous, so this HTML is strictly isolated in an iframe with the strictest sandbox settings and a restrictive Content-Security-Policy."

### 2:15–2:35 — Reliability & AI Architecture
- Briefly summarize the architecture: 
  - "The backend runs FastAPI with PostgreSQL and pgvector for embeddings."
  - "The LLM router seamlessly switches between Anthropic models and local Ollama without code changes."
  - "It includes robust insufficient-evidence handling—refusing to hallucinate if the answer isn't in the transcripts."

### 2:35–2:50 — Closing
*(Show face/camera)*
"This assistant turns Lenny's entire knowledge base into an interactive, trustworthy product management tool. Thank you for evaluating."
