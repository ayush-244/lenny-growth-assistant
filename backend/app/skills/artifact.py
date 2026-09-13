"""Artifact Generation Skill.

This module implements grounded artifact generation (Markdown or HTML/CSS).
It retrieves evidence from the knowledge base, uses the LLM provider to format
the response, and returns structural output.

Generated HTML is wrapped defensively for rendering.
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field

from sqlalchemy.orm import Session as DbSession

from app.agents.grounding import build_retrieval_context, is_insufficient_evidence
from app.core.config import settings
from app.llm import get_llm_provider
from app.rag.retriever import Retriever
from app.schemas.retrieval import RetrievalResult

logger = logging.getLogger(__name__)

# Bounded conversation context: last N messages used for request synthesis.
CONVERSATION_CONTEXT_LIMIT = 4

# Minimum retrieved chunks required.
MIN_EVIDENCE_CHUNKS = 1


@dataclass
class ArtifactSkillResult:
    """Result of an artifact generation attempt."""
    content: str
    artifact_type: str
    provider: str | None = None
    grounded: bool = False
    insufficient_evidence: bool = False
    validation_issues: list[str] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Artifact Generation Prompts
# ---------------------------------------------------------------------------

ARTIFACT_SYSTEM_PROMPT = """You are the Lenny Growth Assistant Artifact Generator.
Your job is to generate a comprehensive {artifact_type} document based on the user's request,
grounded strictly in the retrieved Lenny's Podcast and Newsletter evidence.

CORE RULES:
1. EVIDENCE-ONLY: Only include claims, strategies, and frameworks found in the retrieved evidence.
2. CITATIONS: When mentioning a concept, optionally cite the source/guest inline.
3. NO FABRICATION: Do not invent names, metrics, or frameworks.
4. TYPE: You must generate valid {artifact_type}.
5. METADATA: Do not wrap your response in markdown blocks like ```html unless you are generating markdown. Output the raw {artifact_type} content directly.
"""

HTML_SPECIFIC_INSTRUCTIONS = """
You are generating a standalone HTML artifact.
- Output ONLY valid, clean HTML.
- Use inline CSS or a <style> block in the <head>.
- Create a modern, professional, clean design (e.g., sans-serif fonts, good whitespace, subtle borders).
- DO NOT INCLUDE ANY JavaScript. No <script> tags, no event handlers (onload, onclick).
- DO NOT INCLUDE markdown wrappers (e.g., ```html). Just the HTML starting with <!DOCTYPE html>.
"""

MARKDOWN_SPECIFIC_INSTRUCTIONS = """
You are generating a Markdown artifact.
- Use headings, lists, bolding, and quotes effectively.
- Present the information clearly.
"""


class ArtifactSkill:
    """Skill for generating grounded artifacts."""

    def __init__(self, db_session: DbSession) -> None:
        self.db = db_session
        from app.rag.embeddings import get_embedding_provider
        self.retriever = Retriever(get_embedding_provider())
        # Use configured top_k for thorough artifact context
        self.top_k = settings.rag_top_k

    def run(
        self,
        request: str,
        artifact_type: str,
        recent_history: list[dict[str, str]] | None = None,
        provider_name: str | None = None,
    ) -> ArtifactSkillResult:
        """Run the artifact generation pipeline.

        Parameters
        ----------
        request:
            The user's artifact generation request.
        artifact_type:
            "markdown" or "html".
        recent_history:
            Recent session messages for context.

        Returns
        -------
        ArtifactSkillResult
        """
        t0 = time.perf_counter()
        provider_name = provider_name or settings.model_provider

        # 1. Validate artifact type
        valid_types = {"markdown", "html"}
        if artifact_type not in valid_types:
            return ArtifactSkillResult(
                content=f"Error: Invalid artifact type '{artifact_type}'. Supported types are: {', '.join(valid_types)}.",
                artifact_type="markdown",
                provider=None,
                grounded=False,
                validation_issues=["invalid_artifact_type"],
            )

        # 2. Synthesize context-aware topic
        topic = self._resolve_topic(request, recent_history)
        logger.info("Artifact: resolved topic %r (type=%s)", topic, artifact_type)

        # 3. Retrieve grounding evidence
        retrieval_response = self.retriever.retrieve(
            topic,
            db=self.db,
            top_k=self.top_k,
            min_similarity=settings.rag_min_similarity,
        )
        evidence = retrieval_response.results
        logger.info("Artifact: retrieved %d chunks", len(evidence))

        # 4. Check for insufficient evidence
        if is_insufficient_evidence(evidence) or len(evidence) < MIN_EVIDENCE_CHUNKS:
            logger.info("Artifact: insufficient evidence")
            return ArtifactSkillResult(
                content="I don't have enough evidence in the available Lenny sources to generate a grounded artifact on that topic.",
                artifact_type="markdown",  # Default to markdown for the error message
                provider=None,
                grounded=False,
                insufficient_evidence=True,
                validation_issues=["insufficient_evidence"],
            )

        # 5. Build prompt
        system_instructions = ARTIFACT_SYSTEM_PROMPT.format(artifact_type=artifact_type)
        if artifact_type == "html":
            system_instructions += "\n" + HTML_SPECIFIC_INSTRUCTIONS
        else:
            system_instructions += "\n" + MARKDOWN_SPECIFIC_INSTRUCTIONS
            
        evidence_context = build_retrieval_context(evidence)
        prompt = (
            f"USER REQUEST:\n{request}\n\n"
            f"RESOLVED TOPIC (including conversation context):\n{topic}\n\n"
            f"{evidence_context}\n\n"
            f"Please generate the {artifact_type} artifact now. Remember: NO fabrication, ONLY use retrieved evidence."
        )

        # 6. Call LLM
        provider = get_llm_provider(provider_name)
        llm_response = provider.chat(
            messages=[{"role": "user", "content": prompt}],
            system_prompt=system_instructions,
        )
        
        content = self._clean_llm_output(llm_response.content, artifact_type)
        elapsed_ms = (time.perf_counter() - t0) * 1000

        # Inject CSP meta tag if HTML
        if artifact_type == "html":
            content = self._inject_csp(content)

        logger.info(
            "Artifact: success provider=%r type=%s latency_ms=%.1f",
            provider_name,
            artifact_type,
            elapsed_ms,
        )

        return ArtifactSkillResult(
            content=content,
            artifact_type=artifact_type,
            provider=llm_response.provider,
            grounded=True,
            insufficient_evidence=False,
        )

    def _resolve_topic(self, request: str, recent_history: list[dict[str, str]] | None) -> str:
        """Resolve pronoun references using recent history (like Ship30)."""
        if not recent_history:
            return request

        bounded_history = recent_history[-CONVERSATION_CONTEXT_LIMIT:]
        context_parts = []
        for msg in bounded_history:
            prefix = "User" if msg["role"] == "user" else "Assistant"
            context_parts.append(f"{prefix}: {msg['content']}")
            
        context_str = "\n".join(context_parts)
        return f"Recent Conversation:\n{context_str}\n\nTarget Request: {request}"

    def _clean_llm_output(self, raw: str, artifact_type: str) -> str:
        """Remove markdown wrappers from LLM output if generating HTML."""
        content = raw.strip()
        if artifact_type == "html":
            # Strip ```html ... ``` if LLM ignored the prompt
            if content.startswith("```html"):
                content = content[7:]
            elif content.startswith("```"):
                content = content[3:]
                
            if content.endswith("```"):
                content = content[:-3]
        return content.strip()

    def _inject_csp(self, html_content: str) -> str:
        """Inject a strict CSP meta tag into generated HTML."""
        csp_meta = '<meta http-equiv="Content-Security-Policy" content="default-src \'none\'; style-src \'unsafe-inline\'; img-src data:; font-src data:;">'
        
        # Try to put it in head
        if "<head>" in html_content.lower():
            # Find exact case of <head>
            head_idx = html_content.lower().find("<head>")
            # Insert after <head>
            insert_idx = head_idx + 6
            return html_content[:insert_idx] + "\n" + csp_meta + html_content[insert_idx:]
        elif "<html>" in html_content.lower():
            # No head, create one after html
            html_idx = html_content.lower().find("<html>")
            insert_idx = html_idx + 6
            return html_content[:insert_idx] + "\n<head>\n" + csp_meta + "\n</head>" + html_content[insert_idx:]
        else:
            # Just prepend
            return csp_meta + "\n" + html_content
