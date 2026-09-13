# Design

## The Lenny Growth Assistant

### Target User
The target user is a busy product manager, founder, or growth practitioner who wants direct, actionable insights extracted from Lenny's extensive content library, without hallucinated fluff.

### Core User Journey
1. **Inquiry**: User asks a specific question or requests a long-form essay / artifact.
2. **Contextual Retrieval**: The system pulls exact transcript evidence.
3. **Response**: The user receives a strictly grounded response with inline, clickable citations pointing to specific podcast episodes/newsletters.
4. **Follow-up**: The user can ask follow-up questions; context is bounded to recent turns.
5. **Generative Artifacts**: The user can request structured Markdown or interactive HTML layouts.

### User Interface & Experience

#### 1. Chat UX
- **Familiar Chat Interface**: A clean, persistent message thread.
- **Provider Indicator**: Visual indication of whether the current session is powered by `Anthropic` or `Ollama`.
- **Loading States**: Graceful skeletons and spinners during retrieval and LLM generation.
- **Failure States**: Friendly, non-technical error messages when grounding fails, the LLM errors out, or evidence is insufficient.

#### 2. Citations
- **Inline Linking**: Responses explicitly attribute facts to source episodes.
- **Metadata Bubbles**: Citations include episode titles, guest names, and timestamps where available.

#### 3. Ship30 & Artifact Flow
- **Slash Commands / Explicit Requests**: Users can request a "Ship 30 for 30 essay" or an "HTML Artifact".
- **Two-Pane Layout**: When an artifact is generated, the UI splits into a Chat Pane and an Artifact Viewer Pane.
- **Interactive Previews**: The Artifact Viewer can render both Markdown formatting and interactive HTML/CSS seamlessly.

### Security & Safe HTML Rendering
- **The Threat**: Generated HTML could contain malicious JavaScript (XSS) targeting the parent application.
- **The Mitigation**: The `ArtifactViewer` component uses an `<iframe>` with a strict `sandbox=""` attribute (disallowing `allow-scripts`, `allow-top-navigation`, etc.).
- **Content Security Policy (CSP)**: The iframe injects a restrictive CSP meta tag explicitly forbidding script execution (`script-src 'none'`).
- **No Danger**: React's `dangerouslySetInnerHTML` is explicitly forbidden across the entire codebase to prevent direct DOM injection.
