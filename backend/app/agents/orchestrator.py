"""Grounded conversational agent orchestrator.

The orchestrator is the single main agent in the architecture.

Provider behavior:
- Anthropic uses the retrieval tool through the agentic tool-use loop.
- Ollama retrieves evidence before generation and injects the evidence
  directly into the model prompt for reliable local execution.

Both paths use the same strict REF-N citation validation.
"""

from __future__ import annotations

import logging
from typing import Any

from sqlalchemy.orm import Session

from app.agents.grounding import (
    GROUNDING_SYSTEM_PROMPT,
    RETRIEVE_KNOWLEDGE_TOOL_ANTHROPIC,
    RETRIEVE_KNOWLEDGE_TOOL_OLLAMA,
    build_retrieval_context,
    extract_ref_citations,
)
from app.core.config import settings
from app.llm import LLMError, get_llm_provider
from app.rag.retriever import Retriever
from app.schemas.retrieval import RetrievalResult

logger = logging.getLogger(__name__)


INSUFFICIENT_EVIDENCE_RESPONSE = (
    "I don't have enough evidence in the Lenny knowledge base "
    "to answer that confidently. "
    "The knowledge base doesn't contain relevant information "
    "about this topic."
)


class GroundedConversationalAgent:
    """Main grounded conversational agent."""

    def __init__(self, db_session: Session) -> None:
        self.db = db_session

        self._retriever: Retriever | None = None

        self._current_turn_citations: list[RetrievalResult] = []

        self._ref_mapping: dict[str, RetrievalResult] = {}

        self._next_ref_index: int = 1

    def answer_question(
        self,
        question: str,
        history: list[dict[str, str]] | None = None,
        provider_name: str | None = None,
    ) -> dict[str, Any]:
        """Generate a grounded answer for one user question."""

        messages = list(history) if history else []
        messages.append(
            {
                "role": "user",
                "content": question,
            }
        )

        provider_name = (
            provider_name or settings.model_provider
        ).lower()

        provider = get_llm_provider(provider_name)

        self._current_turn_citations = []
        self._ref_mapping = {}
        self._next_ref_index = 1

        try:
            logger.info(
                "Agent starting turn provider=%r",
                provider_name,
            )

            if provider_name == "ollama":
                response = self._answer_with_ollama(
                    provider=provider,
                    messages=messages,
                    question=question,
                )
            else:
                response = provider.chat(
                    messages=messages,
                    system_prompt=GROUNDING_SYSTEM_PROMPT,
                    tools=(
                        [RETRIEVE_KNOWLEDGE_TOOL_ANTHROPIC]
                        if provider_name == "anthropic"
                        else None
                    ),
                    tool_executor=self._execute_tool,
                )

        except LLMError as exc:
            logger.error(
                "Agent LLM error: %s",
                exc,
            )
            raise

        # ---------------------------------------------------------------
        # Strict citation verification
        # ---------------------------------------------------------------

        cited_refs = extract_ref_citations(
            response.content
        )

        valid_citations: list[RetrievalResult] = []
        seen_chunk_ids: set[Any] = set()

        for ref_label in sorted(cited_refs):
            result = self._ref_mapping.get(ref_label)

            if result is not None and result.chunk_id not in seen_chunk_ids:
                valid_citations.append(result)
                seen_chunk_ids.add(result.chunk_id)

        self._current_turn_citations = valid_citations

        is_grounded = bool(valid_citations)

        # Never trust the model merely because retrieval returned results.
        # The model must explicitly cite a valid retrieved reference.
        if not is_grounded:
            response.content = INSUFFICIENT_EVIDENCE_RESPONSE

        return {
            "answer": response.content,
            "citations": [
                citation.model_dump(mode="json")
                for citation in self._current_turn_citations
            ],
            "grounded": is_grounded,
            "provider": response.provider,
        }

    def _answer_with_ollama(
        self,
        provider: Any,
        messages: list[dict[str, str]],
        question: str,
    ) -> Any:
        """Run the local Ollama path with pre-retrieved evidence.

        Small local models are more reliable when retrieval evidence is
        provided directly instead of requiring an additional tool-call
        decision.
        """

        logger.info(
            "Ollama local path retrieving evidence before generation"
        )

        results = self.retriever.retrieve(
            query=question,
            db=self.db,
            top_k=settings.rag_top_k,
            min_similarity=settings.rag_min_similarity,
        )

        if results.has_results:
            context, ref_mapping = build_retrieval_context(
                results.results,
                start_index=1,
            )

            self._ref_mapping = ref_mapping
            self._current_turn_citations = list(
                results.results
            )
            self._next_ref_index = len(results.results) + 1

            local_system_prompt = (
                GROUNDING_SYSTEM_PROMPT
                + "\n\n"
                + "The retrieved evidence is already provided below. "
                + "Do not call a retrieval tool. "
                + "Use this evidence to answer the user's question.\n\n"
                + context
            )

        else:
            self._ref_mapping = {}
            self._current_turn_citations = []

            local_system_prompt = (
                GROUNDING_SYSTEM_PROMPT
                + "\n\n"
                + "No qualifying knowledge-base evidence was found. "
                + "Do not answer from general knowledge."
            )

        return provider.chat(
            messages=messages,
            system_prompt=local_system_prompt,
            tools=None,
            tool_executor=None,
        )

    @property
    def retriever(self) -> Retriever:
        """Lazily instantiate the retriever."""

        if self._retriever is None:
            from app.rag.embeddings import get_embedding_provider

            self._retriever = Retriever(
                get_embedding_provider()
            )

        return self._retriever

    def _execute_tool(
        self,
        name: str,
        args: dict[str, Any],
    ) -> str:
        """Execute the retrieval tool for the Anthropic agent path."""

        if name != "retrieve_knowledge":
            return f"Error: Unknown tool {name}"

        query = args.get("query", "")

        if not query:
            return "Error: Missing required argument 'query'"

        logger.info(
            "Agent invoking retriever query=%r",
            query,
        )

        results = self.retriever.retrieve(
            query=query,
            db=self.db,
            top_k=settings.rag_top_k,
            min_similarity=settings.rag_min_similarity,
        )

        if not results.has_results:
            logger.info(
                "Agent retriever returned no qualifying results"
            )

            return (
                "No relevant knowledge-base evidence found "
                "for this query."
            )

        logger.info(
            "Agent retrieved %d chunks",
            results.total_found,
        )

        context, new_mapping = build_retrieval_context(
            results.results,
            start_index=self._next_ref_index,
        )

        self._ref_mapping.update(new_mapping)

        self._next_ref_index += len(results.results)

        return context