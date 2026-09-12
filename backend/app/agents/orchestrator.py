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

import json
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
from app.llm import LLMError, LLMRouter, get_llm_provider
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
        # Retriever is created lazily on first use so that test monkeypatches
        # applied to app.rag.embeddings.get_embedding_provider take effect
        # before the provider is resolved.
        self._retriever: Retriever | None = None
        # Store citations collected during the agent loop
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
            Contains keys: "answer" (str), "citations" (list[dict]),
            "grounded" (bool), "provider" (str).
        """
        messages = list(history) if history else []
        messages.append({"role": "user", "content": question})

        provider_name = settings.model_provider.lower()
        provider = get_llm_provider(provider_name)

        tools: list[dict] = []
        if provider_name == "anthropic":
            tools = [RETRIEVE_KNOWLEDGE_TOOL_ANTHROPIC]
        elif provider_name == "ollama":
            tools = [RETRIEVE_KNOWLEDGE_TOOL_OLLAMA]

        # Reset citations for this turn
        self._current_turn_citations = []

        try:
            logger.info("Agent starting turn provider=%r", provider_name)
            response = provider.chat(
                messages=messages,
                system_prompt=GROUNDING_SYSTEM_PROMPT,
                tools=tools if tools else None,
                tool_executor=self._execute_tool,
            )
        except LLMError as exc:
            logger.error("Agent LLM error: %s", exc)
            raise

        # Check if we successfully gathered evidence
        is_grounded = bool(self._current_turn_citations)

        return {
            "answer": response.content,
            "citations": [c.model_dump(mode="json") for c in self._current_turn_citations],
            "grounded": is_grounded,
            "provider": response.provider,
        }

    @property
    def retriever(self) -> Retriever:
        """Lazily instantiated retriever — resolves the embedding provider on
        first access so test monkeypatches are applied before resolution."""
        if self._retriever is None:
            from app.rag.embeddings import get_embedding_provider
            self._retriever = Retriever(get_embedding_provider())
        return self._retriever

    def _execute_tool(self, name: str, args: dict[str, Any]) -> str:
        """Execute a tool called by the LLM and return its result.

        Parameters
        ----------
        name:
            Tool name (must be "retrieve_knowledge").
        args:
            Tool arguments dict (e.g. {"query": "pricing strategy"}).

        Returns
        -------
        str
            The formatted tool result to give back to the LLM.
        """
        if name != "retrieve_knowledge":
            return f"Error: Unknown tool {name}"

        query = args.get("query", "")
        if not query:
            return "Error: Missing required argument 'query'"

        logger.info("Agent invoking retriever query=%r", query)
        results = self.retriever.retrieve(
            query=query,
            db=self.db,
            top_k=settings.rag_top_k,
            min_similarity=settings.rag_min_similarity,
        )

        # Save citations for the API response
        self._current_turn_citations.extend(results.results)

        # De-duplicate citations if the model called the tool multiple times
        # preserving order (first seen)
        seen = set()
        unique_citations = []
        for r in self._current_turn_citations:
            if r.chunk_id not in seen:
                seen.add(r.chunk_id)
                unique_citations.append(r)
        self._current_turn_citations = unique_citations

        if not results.has_results:
            logger.info("Agent retriever returned no qualifying results")
            return "No relevant knowledge-base evidence found for this query."

        logger.info("Agent retrieved %d chunks", results.total_found)
        return build_retrieval_context(results.results)
