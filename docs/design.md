# 🎨 Design

## 🎙️ The Lenny Growth Assistant

---

### 🎯 Target User

The target user is a busy **product manager, founder, or growth practitioner** who wants direct, actionable insights extracted from Lenny's extensive content library, without hallucinated fluff.

---

### 🗺️ Core User Journey

1. ❓ **Inquiry**: User asks a specific question or requests a long-form essay / artifact.

2. 🔎 **Contextual Retrieval**: The system pulls relevant transcript evidence from the knowledge base.

3. 💬 **Response**: The user receives a strictly grounded response with inline, clickable citations pointing to specific podcast episodes/newsletters.

4. 🔄 **Follow-up**: The user can ask follow-up questions; context is bounded to recent turns.

5. 🎨 **Generative Artifacts**: The user can request structured Markdown or interactive HTML layouts.

---

### 📱 User Interface & Experience

#### 1️⃣ Chat UX

- 💬 **Familiar Chat Interface**: A clean, persistent message thread.

- ⚙️ **Provider Indicator**: Visual indication of whether the current session is powered by `Anthropic` or `Ollama`.

- ⏳ **Loading States**: Graceful loading indicators during retrieval and LLM generation.

- ❌ **Failure States**: Friendly, non-technical error messages when grounding fails, the LLM errors out, or evidence is insufficient.

#### 2️⃣ Citations

- 🔗 **Inline Linking**: Responses explicitly attribute facts to source episodes.

- 🏷️ **Metadata Bubbles**: Citations include episode titles, guest names, and timestamps where available.

- 📚 **Evidence Visibility**: Citation metadata is displayed close to the response so users can understand where an answer came from without leaving the conversation.

#### 3️⃣ Ship30 & Artifact Flow

- ⌨️ **Explicit Requests**: Users can request a "Ship 30 for 30 essay" or an "HTML Artifact" through natural-language requests.

- 🪟 **Two-Pane Layout**: When an artifact is generated, the UI splits into a Chat Pane and an Artifact Viewer Pane.

- 👁️ **Interactive Previews**: The Artifact Viewer can render both Markdown formatting and interactive HTML/CSS.

- 📄 **Artifact Context**: Generated artifacts remain associated with the active session so the user can continue the conversation around the generated output.

#### 4️⃣ Interaction States

- 🆕 **Empty State**: New sessions show a concise product introduction, example use cases, and quick prompts to help the user start immediately.

- 🔄 **Loading State**: While retrieval and generation are running, the composer is disabled and a visible loading indicator communicates that the request is being processed.

- ✅ **Success State**: Completed responses display the answer, grounded citations, and relevant source metadata.

- ⚠️ **Insufficient Evidence**: When the knowledge base does not contain enough relevant evidence, the UI clearly states that the system could not find sufficient supporting context rather than presenting an unsupported answer.

- ❌ **Error State**: Backend, model-provider, or retrieval failures are shown as short, user-friendly messages without exposing raw stack traces or internal implementation details.

- 🔌 **Provider Switch State**: The selected provider is shown at session level. During a provider change, the control reflects the pending operation. If the change fails, the previous provider remains selected and the user receives a clear error message.

- 📄 **Artifact State**: Generated artifacts appear in the Artifact Viewer with a clear distinction between Markdown and HTML content.

---

### 📐 Information Architecture

The application is organized around four primary areas:

1. 💬 **Chat**: The primary workspace for asking questions, receiving grounded answers, and continuing conversations.

2. 🧠 **Knowledge Base**: Represents the underlying source corpus used for grounded retrieval and evidence-backed responses.

3. 📄 **Artifacts**: Provides access to generated Markdown and HTML artifacts associated with conversations.

4. 🕘 **History**: Provides access to previous sessions while keeping each session's messages and model configuration isolated.

The desktop interface keeps the active conversation as the primary focus while exposing supporting navigation and evidence alongside it.

---

### 📱 Responsive Behavior

- 🖥️ **Desktop**: The primary experience uses a three-column layout with session navigation, the central chat workspace, and a sources/insights panel.

- 💻 **Tablet**: Secondary panels reduce in width or collapse to preserve sufficient space for the main conversation.

- 📱 **Mobile**: The interface changes to a single-column layout. Sidebar and sources/insights content are accessible through compact navigation controls rather than remaining permanently visible.

- 📐 **Flexible Content**: Chat messages, citations, composer controls, and artifact previews adapt to available width without requiring horizontal scrolling.

- 🪟 **Artifact Viewer**: On smaller screens, the artifact viewer becomes a full-width or stacked view so generated content remains readable and usable.

- 🧩 **Long Content**: Long responses and generated artifacts remain vertically scrollable instead of forcing the overall page to expand horizontally.

---

### ♿ Accessibility

- ⌨️ **Keyboard Navigation**: Interactive controls such as navigation, provider selection, citations, artifact controls, and the message composer are keyboard accessible.

- 🏷️ **Semantic Controls**: Buttons, links, inputs, and navigation elements use appropriate semantic HTML and accessible labels.

- 🎯 **Focus Visibility**: Interactive elements provide a visible focus state for keyboard users.

- 👁️ **Readable UI**: Typography, spacing, and contrast are designed to keep primary content readable across screen sizes.

- 🔊 **Status Communication**: Loading, success, error, and insufficient-evidence states are communicated through visible text rather than relying only on color or animation.

- 🧩 **Accessible Citations**: Citation links expose meaningful source information instead of relying only on icons or abbreviated labels.

- ⌨️ **Composer Interaction**: The message composer supports standard keyboard interaction so users can enter and submit prompts without relying exclusively on pointer input.

- 🛑 **Safe Artifacts**: Generated HTML remains isolated in a sandboxed iframe, maintaining the security boundary while keeping the rendered artifact usable.

---

### 🛡️ Security & Safe HTML Rendering

> **⚠️ The Threat**: Generated HTML could contain malicious JavaScript (XSS) targeting the parent application.

- 📦 **The Mitigation**: The `ArtifactViewer` component uses an `<iframe>` with a strict `sandbox=""` attribute, disallowing script execution and access to the parent application.

- 🔒 **Content Security Policy (CSP)**: The iframe injects a restrictive CSP meta tag explicitly forbidding script execution with `script-src 'none'`.

- 🚫 **No Direct DOM Injection**: React's `dangerouslySetInnerHTML` is explicitly forbidden across the codebase to prevent direct DOM injection.

- 🚫 **No Dynamic Code Execution**: Artifact rendering does not use `eval` or `new Function`.

- 🌐 **Network Isolation**: Generated artifacts are not given access to arbitrary external network resources.

- 🔐 **Parent Application Isolation**: Generated HTML is treated as untrusted content and cannot access the parent application's DOM, cookies, or storage.

- 📝 **Markdown Safety**: Markdown responses are rendered through the application's Markdown renderer without enabling arbitrary raw HTML injection.

---

### 🎨 Visual Design Principles

- **Clarity over decoration**: The interface prioritizes readable answers, evidence, and actions over unnecessary visual elements.

- **Evidence-first design**: Citations and source metadata are visually prominent because trust is central to the product.

- **Conversation-first workflow**: The chat remains the main workspace because users should be able to ask, refine, and follow up without changing context.

- **Progressive disclosure**: Supporting information such as sources, history, and artifacts can be collapsed or moved out of the primary view when screen space is limited.

- **Consistent interaction patterns**: Similar actions use consistent controls, spacing, and visual hierarchy throughout the application.

- **Professional SaaS aesthetic**: The interface uses a polished, modern workspace design suitable for product managers, founders, and growth practitioners.

---

### 🧠 Design Decisions & Trade-offs

- **Chat-first architecture**: The product prioritizes a familiar conversational workflow because the primary job is asking questions and refining insights through follow-up.

- **Three-column desktop layout**: Keeping navigation, chat, and evidence visible at the same time reduces context switching during research.

- **Evidence over visual complexity**: Source metadata and citations are prioritized over decorative UI because trust and traceability are core product requirements.

- **Progressive disclosure**: Secondary information such as sources, history, and artifacts can collapse on smaller screens to keep the main task focused.

- **Session-scoped model selection**: The provider indicator reflects the actual backend session configuration rather than a global UI preference, reducing ambiguity about which model is being used.

- **Safe artifact isolation**: Generated HTML is treated as untrusted content and rendered in a sandboxed iframe rather than injected into the application DOM.

- **Transparency over unsupported answers**: When evidence is insufficient, the interface explicitly communicates the limitation instead of presenting a confident but ungrounded response.

- **Local-first demo support**: Ollama is treated as a first-class model provider for local demonstration and resilience, while Anthropic provides the cloud model option without requiring code changes.

- **Simple information architecture**: The application focuses on Chat, Knowledge Base, Artifacts, and History rather than adding dashboards or advanced analytics that are outside the core user problem.

---

### 🧪 Manual UI Validation Plan

The following flows should be manually verified before submission:

1. **New Session**
   - Create a new session.
   - Confirm the empty state and quick prompts are visible.
   - Confirm the selected provider is displayed correctly.

2. **Grounded Question**
   - Ask a question covered by the knowledge base.
   - Confirm the response contains relevant citation metadata.
   - Confirm the source and timestamp are displayed correctly.

3. **Insufficient Evidence**
   - Ask a question unrelated to the available knowledge base.
   - Confirm the UI clearly reports insufficient evidence.
   - Confirm no fabricated citation is displayed.

4. **Follow-up Question**
   - Ask a grounded question.
   - Ask a related follow-up.
   - Confirm the conversation remains within the same session.

5. **Session Isolation**
   - Create two sessions.
   - Add different questions/messages to each.
   - Switch between them and confirm their histories remain separate.

6. **Provider Switching**
   - Switch between `Ollama` and `Anthropic` where the corresponding configuration is available.
   - Confirm the selected provider is reflected in the current session.
   - Test a failed provider switch and confirm the previous provider remains selected.

7. **Ship30 Essay**
   - Request a Ship 30 for 30 essay.
   - Confirm the generated content follows the expected long-form structure and remains grounded in retrieved evidence.

8. **Artifact Viewer**
   - Request a Markdown artifact.
   - Request an HTML artifact.
   - Confirm both render correctly in the Artifact Viewer.

9. **Responsive Layout**
   - Test desktop, tablet, and mobile viewport sizes.
   - Confirm the layout adapts without horizontal scrolling.
   - Confirm chat remains usable at smaller widths.

10. **Security**
    - Verify generated HTML remains inside the sandboxed Artifact Viewer.
    - Confirm generated content cannot execute arbitrary scripts or access the parent application.

---

### 🏁 Design Goal

The design goal is to make the assistant feel **fast, trustworthy, and practical**.

The interface should help users move from:

**Question → Evidence → Insight → Actionable Artifact**

while making uncertainty visible whenever the available evidence is insufficient.