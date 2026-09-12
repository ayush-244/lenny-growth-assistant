"""Grounding policy for the Lenny Growth Assistant.

This module defines:
- GROUNDING_SYSTEM_PROMPT: The strict system instruction given to the LLM.
- RETRIEVE_KNOWLEDGE_TOOL: Tool definition for the retrieval capability.
- build_retrieval_context(): Formats retrieved chunks for the LLM.
- is_insufficient_evidence(): Detects when retrieval returned no qualifying results.
"""

from __future__ import annotations

from app.schemas.retrieval import RetrievalResult

# ---------------------------------------------------------------------------
# System prompt — the grounding contract
# ---------------------------------------------------------------------------

GROUNDING_SYSTEM_PROMPT = """You are the Lenny Growth Assistant, a specialized knowledge assistant
grounded exclusively in Lenny Rachitsky's podcast episodes and newsletter content.

CORE RULES — YOU MUST FOLLOW THESE WITHOUT EXCEPTION:

1. EVIDENCE-ONLY ANSWERS: For all questions about Lenny's content, strategies, frameworks,
   or advice, you MUST base your answer on retrieved knowledge-base evidence only.
   Do NOT use your pretrained knowledge to fill gaps or supplement retrieved evidence.

2. ALWAYS USE THE RETRIEVAL TOOL: For any substantive question about Lenny's content,
   call the retrieve_knowledge tool first. Only answer after reviewing retrieved evidence.

3. MANDATORY CITATIONS: Every answer that references specific knowledge-base content
   MUST cite the specific episode/source. Use the format:
   [Source: {title} — {guest_name}] or [Source: {title}]

4. NO FABRICATION: Never invent:
   - Episode names or numbers
   - Guest names
   - Timestamps
   - Quotes
   - Source URLs
   - Strategies not mentioned in retrieved evidence

5. INSUFFICIENT EVIDENCE: If retrieval returns no results, or the results are below
   the similarity threshold, you MUST respond with exactly this pattern:
   "I don't have enough evidence in the Lenny knowledge base to answer that confidently.
   The knowledge base doesn't contain relevant information about [topic]."
   Do NOT attempt to answer from general knowledge.

6. CONFLICTING EVIDENCE: If retrieved chunks contradict each other, explicitly state
   the conflict rather than silently choosing one claim.

7. EVIDENCE vs INTERPRETATION: Clearly distinguish between:
   - Direct evidence from retrieved chunks (state what the source says)
   - Your interpretation or synthesis of that evidence (label it as such)

8. GENERAL QUESTIONS: For purely factual, non-Lenny-specific questions (e.g., "what
   is CAC?"), you may answer from general knowledge but state clearly that this is
   general knowledge, not from the Lenny knowledge base.

CITATION FORMAT:
When referencing retrieved evidence, end your answer with a citations section:
Citations:
- [Episode title] featuring [guest] (timestamps: X.Xs - Y.Ys)

The knowledge base is the source of truth. User trust depends on your accuracy."""


# ---------------------------------------------------------------------------
# Tool definition for retrieval
# ---------------------------------------------------------------------------

RETRIEVE_KNOWLEDGE_TOOL_ANTHROPIC = {
    "name": "retrieve_knowledge",
    "description": (
        "Retrieve relevant transcript chunks from the Lenny Growth Assistant knowledge base. "
        "Use this tool for any question about Lenny's podcast content, strategies, frameworks, "
        "or specific episodes. Always call this before answering knowledge-base questions. "
        "Returns the most relevant chunks ranked by semantic similarity."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "query": {
                "type": "string",
                "description": (
                    "The search query to find relevant knowledge-base content. "
                    "Use natural language describing what information you need."
                ),
            }
        },
        "required": ["query"],
    },
}

RETRIEVE_KNOWLEDGE_TOOL_OLLAMA = {
    "type": "function",
    "function": {
        "name": "retrieve_knowledge",
        "description": (
            "Retrieve relevant transcript chunks from the Lenny Growth Assistant knowledge base. "
            "Use this for any question about Lenny's podcast content, strategies, or frameworks. "
            "Returns the most relevant chunks ranked by semantic similarity."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Natural language search query for knowledge-base content.",
                }
            },
            "required": ["query"],
        },
    },
}


# ---------------------------------------------------------------------------
# Context formatting
# ---------------------------------------------------------------------------

def build_retrieval_context(results: list[RetrievalResult]) -> str:
    """Format retrieved chunks into a readable context string for the LLM.

    Parameters
    ----------
    results:
        List of retrieved chunks from the Retriever.

    Returns
    -------
    str
        Formatted context block. Empty string if results is empty.
    """
    if not results:
        return ""

    lines = ["=== RETRIEVED KNOWLEDGE BASE EVIDENCE ===\n"]
    for i, result in enumerate(results, start=1):
        source_parts = [result.title]
        if result.guest_name:
            source_parts.append(f"feat. {result.guest_name}")
        source_label = " — ".join(source_parts)

        ts_info = ""
        if result.timestamp_start is not None and result.timestamp_end is not None:
            ts_info = f" [{result.timestamp_start:.1f}s–{result.timestamp_end:.1f}s]"

        lines.append(
            f"[Chunk {i} | {source_label}{ts_info} | "
            f"similarity={result.similarity_score:.3f} | "
            f"chunk_id={result.chunk_id}]"
        )
        lines.append(result.content)
        lines.append("")

    lines.append("=== END OF RETRIEVED EVIDENCE ===")
    return "\n".join(lines)


def is_insufficient_evidence(results: list[RetrievalResult]) -> bool:
    """Return True if retrieval results are empty or below useful threshold.

    Parameters
    ----------
    results:
        List of retrieved chunks.

    Returns
    -------
    bool
        True if there is no useful evidence to answer the question.
    """
    return len(results) == 0
