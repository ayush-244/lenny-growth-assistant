"""Grounded conversational agent orchestrator.

The Orchestrator is the single main agent in the architecture.
It manages the conversational flow for a single turn:
1. Receives the user question and recent conversation history.
2. Selects the LLM provider via the router.
3. Prepares tools and system prompt.
4. Executes the agentic tool-use loop (handled internally by the provider).
5. Returns a grounded answer and citation metadata.
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
)
from app.core.config import settings
from app.llm import LLMError, get_llm_provider
from app.rag.retriever import Retriever
from app.schemas.retrieval import RetrievalResult

logger = logging.getLogger(__name__)


class GroundedConversationalAgent:
    """The main agent/orchestrator.

    It connects a configured LLMProvider with the RAG Retriever tool,
    enforcing the grounding policy and collecting citations.
    """

    def __init__(self, db_session: Session) -> None:
        self.db = db_session

        # Retriever is created lazily so test monkeypatches applied to
        # the embedding provider take effect before provider resolution.
        self._retriever: Retriever | None = None

        # Store citations collected during the current agent turn.
        self._current_turn_citations: list[RetrievalResult] = []

    def answer_question(
        self,
        question: str,
        history: list[dict[str, str]] | None = None,
    ) -> dict[str, Any]:
        """Generate a grounded answer for the user's question.

        Parameters
        ----------
        question:
            The latest user question.
        history:
            Recent conversation history (roles: user, assistant).

        Returns
        -------
        dict
            Contains:
            - answer: generated answer
            - citations: verified retrieved citations
            - grounded: whether the answer contains a verified citation
            - provider: LLM provider used
        """

        messages = list(history) if history else []
        messages.append(
            {
                "role": "user",
                "content": question,
            }
        )

        provider_name = settings.model_provider.lower()
        provider = get_llm_provider(provider_name)

        tools: list[dict] = []

        if provider_name == "anthropic":
            tools = [RETRIEVE_KNOWLEDGE_TOOL_ANTHROPIC]
        elif provider_name == "ollama":
            tools = [RETRIEVE_KNOWLEDGE_TOOL_OLLAMA]

        # Reset citations for this turn.
        self._current_turn_citations = []

        try:
            logger.info(
                "Agent starting turn provider=%r",
                provider_name,
            )

            response = provider.chat(
                messages=messages,
                system_prompt=GROUNDING_SYSTEM_PROMPT,
                tools=tools if tools else None,
                tool_executor=self._execute_tool,
            )

        except LLMError as exc:
            logger.error(
                "Agent LLM error: %s",
                exc,
            )
            raise

        # Keep only retrieved chunks that the LLM explicitly cited
        # using their exact chunk IDs.
        valid_citations: list[RetrievalResult] = []

        for chunk in self._current_turn_citations:
            if str(chunk.chunk_id) in response.content:
                valid_citations.append(chunk)

        self._current_turn_citations = valid_citations

        # An answer is considered grounded only when at least one
        # retrieved chunk was explicitly cited by the LLM.
        is_grounded = bool(self._current_turn_citations)

        # Deterministic grounding safeguard:
        # if the LLM did not cite any verified retrieved evidence,
        # discard the generated factual answer and return the safe
        # insufficient-evidence response.
        if not is_grounded:
            response.content = (
                "I don't have enough evidence in the Lenny knowledge base "
                "to answer that confidently. "
                "The knowledge base doesn't contain relevant information "
                "about this topic."
            )

        return {
            "answer": response.content,
            "citations": [
                citation.model_dump(mode="json")
                for citation in self._current_turn_citations
            ],
            "grounded": is_grounded,
            "provider": response.provider,
        }

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
        """Execute a tool called by the LLM.

        Parameters
        ----------
        name:
            Tool name. Must be "retrieve_knowledge".

        args:
            Tool arguments, for example:
            {"query": "pricing strategy"}

        Returns
        -------
        str
            Formatted retrieval results for the LLM.
        """

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

        # Save retrieved chunks as candidate citations.
        self._current_turn_citations.extend(
            results.results
        )

        # De-duplicate citations if the model calls the retrieval
        # tool multiple times during the same turn.
        seen: set[Any] = set()
        unique_citations: list[RetrievalResult] = []

        for result in self._current_turn_citations:
            if result.chunk_id not in seen:
                seen.add(result.chunk_id)
                unique_citations.append(result)

        self._current_turn_citations = unique_citations

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

        return build_retrieval_context(
            results.results
        )