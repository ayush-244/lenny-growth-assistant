"""Grounded Ship 30 for 30 essay generation skill."""

from __future__ import annotations

import logging
import re
import time
import uuid
from dataclasses import dataclass, field
from typing import Any

from sqlalchemy.orm import Session as DbSession

from app.agents.grounding import (
    build_retrieval_context,
    extract_ref_citations,
    is_insufficient_evidence,
)
from app.core.config import settings
from app.llm import LLMError, get_llm_provider
from app.logger import log_event
from app.rag.retriever import Retriever
from app.schemas.retrieval import RetrievalResult


logger = logging.getLogger(__name__)


CONVERSATION_CONTEXT_LIMIT = 4

WORD_COUNT_MIN = 1100
WORD_COUNT_MAX = 1400
WORD_COUNT_TARGET = 1250

MAX_GENERATION_ATTEMPTS = 2

MIN_EVIDENCE_CHUNKS = 1
SHIP30_RETRIEVAL_K = 3


INSUFFICIENT_EVIDENCE_MESSAGE = (
    "I don't have enough evidence in the available Lenny sources "
    "to write a grounded Ship 30 for 30 essay on that topic."
)


SHIP30_SYSTEM_PROMPT = f"""You write Ship 30 for 30 essays.

Your task is to write ONE complete essay using ONLY the evidence provided
in the user message.

IMPORTANT:
- You must finish the complete essay.

LENGTH:
- Minimum: {WORD_COUNT_MIN} words.
- Target: {WORD_COUNT_TARGET} words.
- Maximum: {WORD_COUNT_MAX} words.
- Plan the essay before writing.
- Use 6–8 substantial sections.
- Each section should develop the central argument with evidence.
- Do not stop after a short introduction and a few examples.
- The final essay must be at least {WORD_COUNT_MIN} words.
- If the draft is below {WORD_COUNT_MIN} words, continue expanding it before stopping.

GROUNDING:
- Use ONLY the retrieved evidence.
- Never use outside knowledge.
- Never invent facts, quotes, statistics, frameworks, guests, episodes, or strategies.
- If the evidence does not support something, do not include it.

CITATIONS:
- The evidence contains labels such as [REF-1], [REF-2], and [REF-3].
- These are the ONLY citation labels you should use.
- Use the exact labels.
- Do not invent REF numbers.
- Do not write chunk UUIDs.
- Put citations directly after factual claims or paragraphs they support.
- Every section containing information from the evidence must contain a valid [REF-N].
- At the end of the essay, output exactly one line:
  SOURCE_REFS: [REF-1], [REF-2]
- SOURCE_REFS must contain only valid REF-N labels from the retrieved evidence.
- Do not omit SOURCE_REFS.

ESSAY STRUCTURE:
1. Strong specific hook.
2. Explain the problem or tension.
3. Develop ONE central idea.
4. Explain the insight using the evidence.
5. Show practical application.
6. Finish with a clear takeaway.

STYLE:
- Short paragraphs.
- Useful subheadings.
- Bullets only when genuinely useful.
- Natural narrative.
- Practical and specific.
- No generic filler.

OUTPUT:
Return ONLY the complete essay.

Do not include:
- CITATIONS:
- WORD_COUNT:
- metadata
- JSON
- code fences
- any metadata other than SOURCE_REFS

The final line MUST be:
SOURCE_REFS: [REF-1], [REF-2]

Before stopping, make sure:
- The essay is at least {WORD_COUNT_MIN} words.
- The essay contains valid [REF-N] citations.
- The essay is grounded only in the supplied evidence.
"""


@dataclass
class Ship30Result:
    """Result of Ship 30 for 30 essay generation."""

    essay: str
    word_count: int
    citations: list[RetrievalResult]
    provider: str
    grounded: bool
    generation_attempts: int
    insufficient_evidence: bool = False
    validation_issues: list[str] = field(default_factory=list)

    def to_api_dict(self) -> dict[str, Any]:
        """Serialize for API response."""

        return {
            "essay": self.essay,
            "word_count": self.word_count,
            "citations": [
                citation.model_dump(mode="json")
                for citation in self.citations
            ],
            "provider": self.provider,
            "grounded": self.grounded,
            "generation_attempts": self.generation_attempts,
            "insufficient_evidence": self.insufficient_evidence,
            "validation_issues": self.validation_issues,
        }


class Ship30Skill:
    """Generate grounded Ship 30 for 30 essays."""

    def __init__(self, db_session: DbSession) -> None:
        self.db = db_session
        self._retriever: Retriever | None = None

    @property
    def retriever(self) -> Retriever:
        """Create the retriever lazily."""

        if self._retriever is None:
            from app.rag.embeddings import get_embedding_provider

            self._retriever = Retriever(
                get_embedding_provider()
            )

        return self._retriever

    def resolve_topic(
        self,
        request: str,
        recent_history: list[dict[str, str]] | None = None,
    ) -> str:
        """Resolve the essay topic using bounded conversation context."""

        history = recent_history or []
        bounded = history[-CONVERSATION_CONTEXT_LIMIT:]

        if not bounded:
            return request

        request_lower = request.lower().strip()

        reference_triggers = {
            "that",
            "this",
            "the above",
            "it",
            "same topic",
            "write that",
            "write this",
        }

        is_reference = any(
            request_lower.startswith(trigger)
            or f" {trigger} " in request_lower
            for trigger in reference_triggers
        )

        if not is_reference:
            return request

        recent_user = ""
        recent_assistant = ""

        for message in reversed(bounded):
            if message["role"] == "assistant" and not recent_assistant:
                recent_assistant = message["content"][:500]

            elif message["role"] == "user" and not recent_user:
                recent_user = message["content"]

            if recent_user and recent_assistant:
                break

        parts = [request]

        if recent_user:
            parts.append(
                f"Previous question: {recent_user}"
            )

        if recent_assistant:
            parts.append(
                f"Previous answer: {recent_assistant[:300]}"
            )

        return " | ".join(parts)

    def retrieve_evidence(
        self,
        topic: str,
    ) -> list[RetrievalResult]:
        """Retrieve focused evidence for Ship30 generation."""

        response = self.retriever.retrieve(
            query=topic,
            db=self.db,
            top_k=SHIP30_RETRIEVAL_K,
            min_similarity=settings.rag_min_similarity,
        )

        return response.results

    @staticmethod
    def _count_words(text: str) -> int:
        """Count essay words."""

        return len(text.split())

    def validate_word_count(
        self,
        text: str,
    ) -> tuple[bool, int]:
        """Validate essay length."""

        count = self._count_words(text)

        return (
            WORD_COUNT_MIN <= count <= WORD_COUNT_MAX,
            count,
        )

    def validate_citations(
        self,
        cited_ids: set[str],
        retrieved_ids: set[uuid.UUID],
    ) -> tuple[bool, list[str]]:
        """Validate cited chunk IDs against retrieved chunk IDs."""

        retrieved_id_strings = {
            str(chunk_id)
            for chunk_id in retrieved_ids
        }

        invalid = cited_ids - retrieved_id_strings

        return (
            len(invalid) == 0,
            sorted(invalid),
        )

    @staticmethod
    def _clean_output(text: str) -> str:
        """Remove accidental metadata and code fences."""

        content = text.strip()

        if content.startswith("```markdown"):
            content = content[len("```markdown"):].strip()

        elif content.startswith("```"):
            content = content[3:].strip()

        if content.endswith("```"):
            content = content[:-3].strip()

        lines = content.splitlines()
        cleaned: list[str] = []

        for line in lines:
            stripped = line.strip()

            if stripped == "---":
                break

            if stripped.startswith("CITATIONS:"):
                continue

            if stripped.startswith("SOURCE_REFS:"):
                continue

            if stripped.startswith("WORD_COUNT:"):
                continue

            cleaned.append(line)

        return "\n".join(cleaned).strip()

    @staticmethod
    def _remove_internal_refs(text: str) -> str:
        """Remove internal retrieval reference labels from user-facing output."""

        cleaned = re.sub(r"\[REF-\d+\]", "", text)
        cleaned = re.sub(r"\n{3,}", "\n\n", cleaned)
        return cleaned.strip()

    def _parse_llm_output(
        self,
        raw: str,
        retrieved_chunks: list[RetrievalResult],
    ) -> tuple[str, set[str], int]:
        """Parse essay prose and legacy UUID citation metadata."""

        lines = raw.splitlines()

        essay_lines: list[str] = []
        cited_ids: set[str] = set()
        metadata_started = False

        for line in lines:
            stripped = line.strip()

            if stripped == "---":
                metadata_started = True
                continue

            if stripped.startswith("CITATIONS:"):
                metadata_started = True

                raw_ids = stripped[len("CITATIONS:"):].strip()

                if raw_ids:
                    ref_ids = re.findall(
                        r"\[REF-\d+\]",
                        raw_ids,
                        flags=re.IGNORECASE,
                    )

                    if ref_ids:
                        cited_ids.update(
                            ref_id.strip("[]").upper()
                            for ref_id in ref_ids
                        )
                    else:
                        for part in raw_ids.split(","):
                            citation_id = part.strip()

                            if citation_id:
                                cited_ids.add(citation_id)

                continue

            if stripped.startswith("SOURCE_REFS:"):
                metadata_started = True

                raw_refs = stripped[len("SOURCE_REFS:"):].strip()

                if raw_refs:
                    cited_ids.update(
                        ref_id.strip("[]").upper()
                        for ref_id in re.findall(
                            r"\[REF-\d+\]",
                            raw_refs,
                            flags=re.IGNORECASE,
                        )
                    )

                continue

            if stripped.startswith("WORD_COUNT:"):
                metadata_started = True
                continue

            if not metadata_started:
                essay_lines.append(line)

        essay = "\n".join(essay_lines).strip()

        if not essay:
            essay = raw.strip()

        word_count = self._count_words(essay)

        return essay, cited_ids, word_count

    def generate_essay(
        self,
        topic: str,
        evidence: list[RetrievalResult],
        provider_name: str | None = None,
        retry_feedback: str | None = None,
        previous_essay: str | None = None,
    ) -> tuple[str, str]:
        """Generate an essay using retrieved evidence."""

        provider_name = (
            provider_name or settings.model_provider
        ).lower()

        provider = get_llm_provider(
            provider_name
        )

        context, _ = build_retrieval_context(
            evidence,
            start_index=1,
        )

        retry_instruction = ""

        if retry_feedback:
            retry_instruction = (
                "\n\nCORRECTION REQUIRED:\n"
                f"{retry_feedback}\n"
                "\nThe previous draft is included below. "
                "Do NOT start over from scratch. "
                "Keep its useful structure and evidence-backed ideas, "
                "then expand it until it reaches the required length.\n"
                "\nPREVIOUS DRAFT:\n"
                f"{previous_essay or ''}\n"
                "\nEXPANSION REQUIREMENTS:\n"
                f"- Previous draft length: {len((previous_essay or '').split())} words.\n"
                f"- Expand the draft to approximately {WORD_COUNT_TARGET} words.\n"
                f"- Final length must be between {WORD_COUNT_MIN} and {WORD_COUNT_MAX} words.\n"
                "- Add useful explanation, narrative, examples, and practical implications "
                "ONLY when supported by the retrieved evidence.\n"
                "- Preserve valid [REF-N] citations.\n"
                "- Do not shorten the previous draft.\n"
                "- Do not introduce outside knowledge.\n"
            )

        user_message = (
            "Write a complete Ship 30 for 30 essay about:\n\n"
            f"{topic}\n\n"
            "Use ONLY the retrieved evidence below.\n"
            f"The essay must contain {WORD_COUNT_MIN}â€“"
            f"{WORD_COUNT_MAX} words.\n"
            "Target approximately "
            f"{WORD_COUNT_TARGET} words.\n"
            "Use the exact [REF-N] labels from the evidence "
            "to cite factual claims.\n"
            "Do not use UUIDs.\n"
            f"{retry_instruction}\n"
            "RETRIEVED EVIDENCE:\n\n"
            f"{context}"
        )

        logger.info(
            "Ship30: generating provider=%r "
            "evidence_chunks=%d retry=%s",
            provider_name,
            len(evidence),
            bool(retry_feedback),
        )

        response = provider.chat(
            messages=[
                {
                    "role": "user",
                    "content": user_message,
                }
            ],
            system_prompt=SHIP30_SYSTEM_PROMPT,
            tools=None,
            tool_executor=None,
        )

        return response.content, response.provider

    def run(
        self,
        request: str,
        recent_history: list[dict[str, str]] | None = None,
        provider_name: str | None = None,
    ) -> Ship30Result:
        """Execute grounded Ship30 generation."""

        started = time.perf_counter()

        provider_name = (
            provider_name or settings.model_provider
        ).lower()

        topic = self.resolve_topic(
            request,
            recent_history,
        )

        logger.info(
            "Ship30: resolved topic=%r",
            topic[:120],
        )

        evidence = self.retrieve_evidence(
            topic
        )

        logger.info(
            "Ship30: retrieved %d chunks",
            len(evidence),
        )

        if (
            is_insufficient_evidence(evidence)
            or len(evidence) < MIN_EVIDENCE_CHUNKS
        ):
            log_event(
                "ship30_insufficient_evidence",
                retrieved=len(evidence),
                topic=topic[:80],
            )

            return Ship30Result(
                essay=INSUFFICIENT_EVIDENCE_MESSAGE,
                word_count=self._count_words(
                    INSUFFICIENT_EVIDENCE_MESSAGE
                ),
                citations=[],
                provider=provider_name,
                grounded=False,
                generation_attempts=0,
                insufficient_evidence=True,
                validation_issues=[
                    "insufficient_evidence"
                ],
            )

        ref_mapping = {
            f"REF-{index}": result
            for index, result in enumerate(
                evidence,
                start=1,
            )
        }

        retrieved_ids = {
            result.chunk_id
            for result in evidence
        }

        best_result: Ship30Result | None = None
        previous_generated_essay: str | None = None
        all_issues: list[str] = []

        for attempt in range(
            1,
            MAX_GENERATION_ATTEMPTS + 1,
        ):
            logger.info(
                "Ship30: generation attempt=%d",
                attempt,
            )

            retry_feedback = None

            if attempt > 1:
                previous_word_count = (
                    len(best_result.essay.split())
                    if best_result is not None
                    else 0
                )
                minimum_words_to_add = max(
                    150,
                    WORD_COUNT_MIN - previous_word_count + 100,
                )

                retry_feedback = (
                    "The previous attempt failed validation. "
                    "Treat the previous draft below as the base draft and "
                    "EXPAND it rather than starting over. "
                    f"The previous draft contains {previous_word_count} words. "
                    f"The final essay MUST contain at least {WORD_COUNT_MIN} words "
                    f"and should target {WORD_COUNT_TARGET} words. "
                    f"Add at least {minimum_words_to_add} new words. "
                    "Do not shorten, summarize, or replace the previous draft. "
                    "Keep its useful evidence-backed ideas and structure. "
                    "Add substantive explanation, narrative development, "
                    "practical application, and transitions using ONLY the "
                    "retrieved evidence. "
                    "Preserve valid [REF-N] citations and add citations where "
                    "new factual claims require them. "
                    "Finish with a SOURCE_REFS line containing the valid REF-N labels used. "
                    "Do not stop until the minimum word count is reached."
                )

            try:
                raw_output, actual_provider = (
                    self.generate_essay(
                        topic=topic,
                        evidence=evidence,
                        provider_name=provider_name,
                        retry_feedback=retry_feedback,
                        previous_essay=previous_generated_essay,
                    )
                )

            except LLMError:
                raise

            parsed_essay, legacy_cited_ids, _ = (
                self._parse_llm_output(
                    raw_output,
                    evidence,
                )
            )

            essay = self._clean_output(
                parsed_essay
            )

            cited_refs = extract_ref_citations(
                essay
            )

            metadata_ref_citations = {
                citation_id
                for citation_id in legacy_cited_ids
                if citation_id.startswith("REF-")
            }

            cited_refs = cited_refs | metadata_ref_citations

            visible_essay = self._remove_internal_refs(
                essay
            )

            word_count = self._count_words(
                visible_essay
            )

            word_count_valid = (
                WORD_COUNT_MIN
                <= word_count
                <= WORD_COUNT_MAX
            )

            invalid_refs = {
                ref
                for ref in cited_refs
                if ref not in ref_mapping
            }

            ref_citations_valid = (
                bool(cited_refs)
                and not invalid_refs
            )

            legacy_uuid_ids = {
                citation_id
                for citation_id in legacy_cited_ids
                if not citation_id.startswith("REF-")
            }

            legacy_citations_valid, invalid_legacy_ids = (
                self.validate_citations(
                    legacy_uuid_ids,
                    retrieved_ids,
                )
            )

            has_legacy_citations = bool(
                legacy_uuid_ids
            )

            citation_valid = (
                ref_citations_valid
                or (
                    has_legacy_citations
                    and legacy_citations_valid
                )
            )

            cited_chunks: list[RetrievalResult] = []

            for ref in sorted(cited_refs):
                result = ref_mapping.get(ref)

                if result is not None:
                    cited_chunks.append(result)

            for result in evidence:
                if str(result.chunk_id) in legacy_uuid_ids:
                    if result not in cited_chunks:
                        cited_chunks.append(result)

            issues: list[str] = []

            if not word_count_valid:
                issues.append(
                    f"word_count_out_of_range: "
                    f"{word_count}"
                )

            if not citation_valid:
                if not cited_refs and not legacy_uuid_ids:
                    issues.append(
                        "missing_citations"
                    )
                elif invalid_refs:
                    issues.append(
                        f"invalid_citations: "
                        f"{sorted(invalid_refs)}"
                    )
                elif invalid_legacy_ids:
                    issues.append(
                        f"invalid_citations: "
                        f"{sorted(invalid_legacy_ids)}"
                    )

            all_issues.extend(
                issues
            )

            current = Ship30Result(
                essay=visible_essay,
                word_count=word_count,
                citations=cited_chunks,
                provider=actual_provider,
                grounded=citation_valid,
                generation_attempts=attempt,
                insufficient_evidence=False,
                validation_issues=issues,
            )

            best_result = current
            previous_generated_essay = essay

            if not issues:
                elapsed_ms = (
                    time.perf_counter()
                    - started
                ) * 1000

                logger.info(
                    "Ship30: success attempt=%d "
                    "word_count=%d citations=%d "
                    "latency_ms=%.1f",
                    attempt,
                    word_count,
                    len(cited_chunks),
                    elapsed_ms,
                )

                return current

            if attempt < MAX_GENERATION_ATTEMPTS:
                logger.warning(
                    "Ship30: validation failed; "
                    "retrying issues=%r",
                    issues,
                )

        assert best_result is not None

        if not best_result.grounded:
            best_result.essay = (
                "I couldn't safely generate a grounded "
                "Ship 30 essay because the generated "
                "content was discarded after failing "
                "citation validation."
            )

            best_result.word_count = (
                self._count_words(
                    best_result.essay
                )
            )

            best_result.citations = []

        best_result.validation_issues = (
            all_issues
        )

        elapsed_ms = (
            time.perf_counter()
            - started
        ) * 1000

        logger.warning(
            "Ship30: generation failed validation "
            "attempts=%d issues=%r latency_ms=%.1f",
            MAX_GENERATION_ATTEMPTS,
            all_issues,
            elapsed_ms,
        )

        return best_result