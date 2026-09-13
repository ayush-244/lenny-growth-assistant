"""Ship 30 for 30 essay skill.

This module implements grounded essay generation in the Ship 30 for 30 format.

Design
------
The Ship30Skill takes a user request and session context and produces a
~1,250-word essay grounded in retrieved Lenny knowledge-base evidence.

Key guarantees:
- ALL Lenny-specific claims must be supported by retrieved evidence.
- Citations map to actual retrieved chunks — no fabrication.
- Word count is validated; bounded regeneration (max 2 attempts) is enforced.
- Conversation context is bounded to the last 4 messages (2 turns).
- Insufficient evidence produces a transparent response, not a fake essay.
- Provider is consumed from the existing LLMProvider abstraction.
- No hardcoded provider references.

Generation Flow
---------------
1. resolve_topic()       — extract topic from request + last ≤4 messages
2. retrieve_evidence()   — use existing Retriever for RAG
3. validate_evidence()   — check we have enough to write grounded content
4. generate_essay()      — call LLM with Ship30 system prompt + retrieved context
5. validate_word_count() — check 1,100–1,400 range
6. validate_citations()  — ensure cited chunk_ids exist in retrieved set
7. If validation fails → attempt once more (max 2 total attempts)
8. Return Ship30Result with best result, metadata, and any deviation flags
"""

from __future__ import annotations

import logging
import time
import uuid
from dataclasses import dataclass, field
from typing import Any

from sqlalchemy.orm import Session as DbSession

from app.agents.grounding import build_retrieval_context, is_insufficient_evidence
from app.core.config import settings
from app.llm import LLMError, get_llm_provider
from app.rag.retriever import Retriever
from app.schemas.retrieval import RetrievalResult
from app.logger import log_event

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

#: Bounded conversation context: last N messages used for topic resolution.
CONVERSATION_CONTEXT_LIMIT = 4

#: Acceptable word count range for Ship30 essays.
WORD_COUNT_MIN = 1100
WORD_COUNT_MAX = 1400
WORD_COUNT_TARGET = 1250

#: Maximum number of generation attempts before returning best result.
MAX_GENERATION_ATTEMPTS = 2

#: Minimum retrieved chunks required to write a grounded essay.
MIN_EVIDENCE_CHUNKS = 1


# ---------------------------------------------------------------------------
# Ship30 system prompt
# ---------------------------------------------------------------------------

SHIP30_SYSTEM_PROMPT = f"""You are an expert writer creating essays in the Ship 30 for 30 format.

You will be given retrieved evidence from Lenny Rachitsky's podcast and newsletter.
Your ONLY job is to write a grounded essay using that evidence.

STRICT RULES:

1. GROUNDING: Every Lenny-specific claim MUST come from the provided retrieved evidence.
   Do NOT use general knowledge to fill gaps. Do NOT invent frameworks, quotes, or strategies.

2. TARGET LENGTH: Write approximately {WORD_COUNT_TARGET} words of essay prose.
   Acceptable range: {WORD_COUNT_MIN}–{WORD_COUNT_MAX} words.
   Count only the essay body — not headings, citations, or metadata lines.

3. STRONG HOOK: Open with a specific, concrete observation, tension, or contradiction.
   Do NOT open with generic statements like "Growth is important" or "Product management is key."
   The first paragraph must create a reason to keep reading.

4. ONE CENTRAL IDEA: The essay must argue one clear insight or lesson. Do not dump
   multiple unrelated topics into a single essay.

5. NARRATIVE: Use story → situation → realization → lesson → application where the
   evidence supports it. Avoid dry summaries of what the podcast said.

6. SKIMMABLE STRUCTURE:
   - Short paragraphs (2–4 sentences)
   - Meaningful subheadings where appropriate
   - Bullets only where they genuinely help clarity
   - Clear transitions between sections

7. PRACTICAL VALUE: End with a concrete takeaway that tells the reader what to do differently.
   Ground this in the retrieved evidence.

8. HONESTY: If the retrieved evidence only partially supports the essay topic, acknowledge it.
   A shorter grounded essay is better than a longer unsupported one.
   Never fabricate episode names, guest names, quotes, or statistics.

9. CITATIONS IN PROSE: When referencing specific insights from the evidence, use inline
   attribution like: "According to [Episode Title]" or "As [Guest Name] explained..."
   Reference chunk_ids at the end in a CITATIONS section using the format:
   CITATIONS: chunk_id_1, chunk_id_2, ...
   Only list chunk_ids that you actually referenced in the essay.

10. NO FABRICATION: If you cannot find strong evidence, do not invent it. State clearly:
    "Note: The available evidence on this topic is limited to [what you found]."

OUTPUT FORMAT:
Write the essay prose directly. End with:
---
CITATIONS: <comma-separated chunk_ids you actually referenced>
WORD_COUNT: <integer count of essay prose words>
"""


# ---------------------------------------------------------------------------
# Result dataclass
# ---------------------------------------------------------------------------

@dataclass
class Ship30Result:
    """Result of a Ship30 essay generation attempt.

    Attributes
    ----------
    essay: The generated essay prose (without citation/metadata lines).
    word_count: Actual word count of the essay prose.
    citations: List of RetrievalResult objects corresponding to cited chunks.
    provider: Provider name that generated the essay.
    grounded: True if the essay is backed by retrieved evidence.
    generation_attempts: Number of generation attempts made (1 or 2).
    insufficient_evidence: True if retrieval returned too little to write.
    validation_issues: List of validation failure reasons (for logging/metadata).
    retrieved_chunk_ids: Set of chunk UUIDs that were retrieved (for validation).
    """

    essay: str
    word_count: int
    citations: list[RetrievalResult]
    provider: str
    grounded: bool
    generation_attempts: int
    insufficient_evidence: bool = False
    validation_issues: list[str] = field(default_factory=list)
    retrieved_chunk_ids: set[uuid.UUID] = field(default_factory=set)

    def to_api_dict(self) -> dict[str, Any]:
        """Serialize for API response."""
        return {
            "essay": self.essay,
            "word_count": self.word_count,
            "citations": [c.model_dump(mode="json") for c in self.citations],
            "provider": self.provider,
            "grounded": self.grounded,
            "generation_attempts": self.generation_attempts,
            "insufficient_evidence": self.insufficient_evidence,
            "validation_issues": self.validation_issues,
        }


# ---------------------------------------------------------------------------
# Ship30Skill
# ---------------------------------------------------------------------------

class Ship30Skill:
    """Grounded Ship 30 essay generation skill.

    Responsible for:
    - Topic resolution from request + bounded conversation context
    - Evidence retrieval using the existing Retriever
    - Essay generation via the configured LLM provider
    - Word-count and citation validation
    - Bounded regeneration (max 2 attempts)
    - Transparent insufficient-evidence handling
    """

    def __init__(self, db_session: DbSession) -> None:
        self.db = db_session
        self._retriever: Retriever | None = None

    @property
    def retriever(self) -> Retriever:
        """Lazy retriever — respects monkeypatches in tests."""
        if self._retriever is None:
            from app.rag.embeddings import get_embedding_provider
            self._retriever = Retriever(get_embedding_provider())
        return self._retriever

    def resolve_topic(
        self,
        request: str,
        recent_history: list[dict[str, str]] | None = None,
    ) -> str:
        """Extract the essay topic from the request and bounded conversation context.

        Uses at most the last CONVERSATION_CONTEXT_LIMIT (4) messages.
        Pronoun references like "that", "this", "the above" are resolved
        using the most recent user question + assistant answer.

        Parameters
        ----------
        request: The current user's essay request.
        recent_history: Recent messages [{role, content}, ...], newest last.

        Returns
        -------
        str: A resolved topic string suitable for retrieval queries.
        """
        history = recent_history or []
        # Bound to last CONVERSATION_CONTEXT_LIMIT messages
        bounded = history[-CONVERSATION_CONTEXT_LIMIT:]

        # Detect pronoun/reference patterns that indicate the request
        # refers to the previous conversation turn.
        reference_triggers = {
            "that", "this", "the above", "it", "same topic",
            "turn that", "turn this", "write that", "write this",
            "write an essay about that", "write an essay about this",
        }
        request_lower = request.lower().strip()
        is_pronoun_reference = any(
            request_lower.startswith(trigger) or f" {trigger} " in request_lower
            for trigger in reference_triggers
        )

        if is_pronoun_reference and bounded:
            # Find the most recent user question and assistant answer
            recent_user = ""
            recent_assistant = ""
            for msg in reversed(bounded):
                if msg["role"] == "assistant" and not recent_assistant:
                    recent_assistant = msg["content"][:500]
                elif msg["role"] == "user" and not recent_user:
                    recent_user = msg["content"]
                if recent_user and recent_assistant:
                    break

            # Build a rich topic from request + previous turn context
            parts = [request]
            if recent_user:
                parts.append(f"Context from previous question: {recent_user}")
            if recent_assistant:
                parts.append(f"Context from previous answer: {recent_assistant[:200]}")
            return " | ".join(parts)

        return request

    def retrieve_evidence(self, topic: str) -> list[RetrievalResult]:
        """Retrieve relevant knowledge-base chunks for the given topic.

        Parameters
        ----------
        topic: Resolved topic string.

        Returns
        -------
        list[RetrievalResult]: Retrieved chunks sorted by similarity descending.
        """
        response = self.retriever.retrieve(
            query=topic,
            db=self.db,
            top_k=settings.rag_top_k,
            min_similarity=settings.rag_min_similarity,
        )
        return response.results

    def _count_words(self, text: str) -> int:
        """Count words in essay prose (whitespace-split)."""
        return len(text.split())

    def validate_word_count(self, text: str) -> tuple[bool, int]:
        """Return (is_valid, word_count) for the essay prose.

        Parameters
        ----------
        text: Essay prose only (no citation/metadata lines).

        Returns
        -------
        tuple[bool, int]: (within_range, actual_count)
        """
        count = self._count_words(text)
        return WORD_COUNT_MIN <= count <= WORD_COUNT_MAX, count

    def validate_citations(
        self,
        cited_ids: set[str],
        retrieved_ids: set[uuid.UUID],
    ) -> tuple[bool, list[str]]:
        """Validate that all cited chunk IDs exist in the retrieved set.

        Parameters
        ----------
        cited_ids: chunk_ids referenced by the LLM in the essay as strings.
        retrieved_ids: chunk_ids that were actually retrieved for this request.

        Returns
        -------
        tuple[bool, list[str]]: (all_valid, list_of_invalid_ids_as_strings)
        """
        retrieved_id_strs = {str(uid) for uid in retrieved_ids}
        invalid = cited_ids - retrieved_id_strs
        return len(invalid) == 0, list(invalid)

    def _parse_llm_output(
        self,
        raw: str,
        retrieved_chunks: list[RetrievalResult],
    ) -> tuple[str, set[str], int]:
        """Parse LLM output into (essay_prose, cited_chunk_ids, word_count).

        The LLM is instructed to end its output with:
          ---
          CITATIONS: chunk_id_1, chunk_id_2, ...
          WORD_COUNT: <integer>

        Parameters
        ----------
        raw: Raw LLM text output.
        retrieved_chunks: The retrieved chunks (used for fallback matching).

        Returns
        -------
        tuple[str, set[str], int]:
            (essay_prose, set_of_cited_chunk_ids_as_strings, self_reported_or_counted_word_count)
        """
        # Split on the separator "---" (or just look for CITATIONS: line)
        essay_part = raw
        cited_ids: set[str] = set()

        # Try to find and parse CITATIONS line
        lines = raw.split("\n")
        essay_lines = []
        in_metadata = False
        for line in lines:
            stripped = line.strip()
            if stripped == "---" or stripped.startswith("CITATIONS:") or stripped.startswith("WORD_COUNT:"):
                in_metadata = True
            if in_metadata:
                if stripped.startswith("CITATIONS:"):
                    raw_ids = stripped.replace("CITATIONS:", "").strip()
                    for part in raw_ids.split(","):
                        cid = part.strip()
                        if cid:
                            cited_ids.add(cid)
            else:
                essay_lines.append(line)

        essay_part = "\n".join(essay_lines).strip()
        if not essay_part:
            # Fallback: use everything if parsing failed
            essay_part = raw.strip()

        # Count words in prose
        word_count = self._count_words(essay_part)

        return essay_part, cited_ids, word_count

    def generate_essay(
        self,
        topic: str,
        evidence: list[RetrievalResult],
    ) -> tuple[str, str]:
        """Generate a Ship30 essay from the given evidence.

        Parameters
        ----------
        topic: The resolved essay topic.
        evidence: Retrieved knowledge-base chunks.

        Returns
        -------
        tuple[str, str]: (raw_llm_output, provider_name)

        Raises
        ------
        LLMError: If the configured provider is unavailable.
        """
        provider_name = settings.model_provider.lower()
        provider = get_llm_provider(provider_name)

        context = build_retrieval_context(evidence)

        user_message = (
            f"Write a Ship 30 for 30 essay about the following topic:\n\n"
            f"TOPIC: {topic}\n\n"
            f"Use the retrieved evidence below as your source material.\n\n"
            f"{context}"
        )

        logger.info(
            "Ship30: generating essay provider=%r topic=%r evidence_chunks=%d",
            provider_name,
            topic[:80],
            len(evidence),
        )

        response = provider.chat(
            messages=[{"role": "user", "content": user_message}],
            system_prompt=SHIP30_SYSTEM_PROMPT,
            tools=None,
            tool_executor=None,
        )

        return response.content, response.provider

    def run(
        self,
        request: str,
        recent_history: list[dict[str, str]] | None = None,
    ) -> Ship30Result:
        """Execute the full Ship30 generation pipeline.

        Parameters
        ----------
        request: The user's essay generation request.
        recent_history: Recent session messages (newest last). Bounded to 4 internally.

        Returns
        -------
        Ship30Result: The best result after up to MAX_GENERATION_ATTEMPTS attempts.
        """
        t0 = time.perf_counter()
        session_log: dict[str, Any] = {
            "operation": "ship30_generation",
            "provider": settings.model_provider,
        }

        # --- 1. Resolve topic ---
        topic = self.resolve_topic(request, recent_history)
        logger.info("Ship30: resolved topic=%r", topic[:100])

        # --- 2. Retrieve evidence ---
        evidence = self.retrieve_evidence(topic)
        retrieved_ids: set[uuid.UUID] = {r.chunk_id for r in evidence}

        session_log["retrieval_count"] = len(evidence)

        # --- 3. Check for insufficient evidence ---
        if is_insufficient_evidence(evidence) or len(evidence) < MIN_EVIDENCE_CHUNKS:
            log_event(
                "ship30_insufficient_evidence",
                retrieved=len(evidence),
                topic=topic[:80],
            )
            insufficient_msg = (
                "I don't have enough evidence in the available Lenny sources "
                f"to write a grounded Ship 30 essay on that topic. "
                f"The knowledge base returned {len(evidence)} relevant chunks, "
                f"which is below the minimum required for a grounded essay. "
                f"Please try a topic that is more directly covered in Lenny's "
                f"podcast or newsletter content."
            )
            return Ship30Result(
                essay=insufficient_msg,
                word_count=self._count_words(insufficient_msg),
                citations=[],
                provider=settings.model_provider,
                grounded=False,
                generation_attempts=0,
                insufficient_evidence=True,
                validation_issues=["insufficient_evidence"],
                retrieved_chunk_ids=retrieved_ids,
            )

        # --- 4. Generation loop (max MAX_GENERATION_ATTEMPTS attempts) ---
        best_result: Ship30Result | None = None
        all_validation_issues: list[str] = []

        for attempt in range(1, MAX_GENERATION_ATTEMPTS + 1):
            logger.info("Ship30: generation attempt=%d", attempt)

            try:
                raw_output, provider_name = self.generate_essay(topic, evidence)
            except LLMError as exc:
                logger.error("Ship30: LLM error on attempt=%d: %s", attempt, exc)
                raise

            # --- 5. Parse output ---
            essay_prose, cited_ids, reported_word_count = self._parse_llm_output(
                raw_output, evidence
            )

            # --- 6. Validate word count ---
            wc_valid, actual_word_count = self.validate_word_count(essay_prose)

            # --- 7. Validate citations ---
            citations_valid, invalid_citation_ids = self.validate_citations(
                cited_ids, retrieved_ids
            )

            # Resolve cited chunks to RetrievalResult objects
            cited_chunks: list[RetrievalResult] = [
                r for r in evidence if str(r.chunk_id) in cited_ids
            ]
            # If no citations were parsed, attribute all retrieved chunks
            # (conservative: don't return zero citations for a grounded essay)
            if not cited_chunks and evidence:
                cited_chunks = evidence

            attempt_issues: list[str] = []
            if not wc_valid:
                issue = f"word_count_out_of_range: {actual_word_count} (expected {WORD_COUNT_MIN}–{WORD_COUNT_MAX})"
                attempt_issues.append(issue)
                logger.warning("Ship30: attempt=%d %s", attempt, issue)

            if not citations_valid:
                issue = f"invalid_citations: {invalid_citation_ids}"
                attempt_issues.append(issue)
                logger.warning("Ship30: attempt=%d %s", attempt, issue)

            all_validation_issues.extend(attempt_issues)

            current_result = Ship30Result(
                essay=essay_prose,
                word_count=actual_word_count,
                citations=cited_chunks,
                provider=provider_name,
                grounded=True,
                generation_attempts=attempt,
                validation_issues=attempt_issues,
                retrieved_chunk_ids=retrieved_ids,
            )

            if not attempt_issues:
                # Validation passed — return immediately
                elapsed_ms = (time.perf_counter() - t0) * 1000
                logger.info(
                    "Ship30: success attempt=%d provider=%r word_count=%d "
                    "citations=%d latency_ms=%.1f",
                    attempt,
                    provider_name,
                    actual_word_count,
                    len(cited_chunks),
                    elapsed_ms,
                )
                current_result.validation_issues = []
                return current_result

            # Keep best result in case both attempts fail
            best_result = current_result

            if attempt < MAX_GENERATION_ATTEMPTS:
                logger.info(
                    "Ship30: attempt=%d failed validation, retrying. issues=%r",
                    attempt,
                    attempt_issues,
                )

        # --- Both attempts exhausted — return best result with issues recorded ---
        assert best_result is not None
        elapsed_ms = (time.perf_counter() - t0) * 1000

        # PROSE SAFETY REQUIREMENT
        # If the best result failed citation validation, we cannot safely return the prose.
        failed_citation_val = any("invalid_citations" in issue for issue in best_result.validation_issues)
        if failed_citation_val:
            best_result.essay = (
                "Generation failed: The model repeatedly produced claims backed by fabricated citations "
                "that were not present in the retrieved evidence. To ensure strict grounding, "
                "the unsupported essay has been discarded."
            )
            best_result.word_count = self._count_words(best_result.essay)
            best_result.citations = []
            best_result.grounded = False

        logger.warning(
            "Ship30: all %d attempts failed validation. Returning best result. "
            "provider=%r word_count=%d citations=%d issues=%r latency_ms=%.1f",
            MAX_GENERATION_ATTEMPTS,
            best_result.provider,
            best_result.word_count,
            len(best_result.citations),
            all_validation_issues,
            elapsed_ms,
        )
        best_result.validation_issues = all_validation_issues
        return best_result
