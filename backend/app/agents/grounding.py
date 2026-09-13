"""Grounding policy for the Lenny Growth Assistant.

This module defines:
- GROUNDING_SYSTEM_PROMPT: The strict system instruction given to the LLM.
- RETRIEVE_KNOWLEDGE_TOOL: Tool definition for the retrieval capability.
- build_retrieval_context(): Formats retrieved chunks for the LLM with
  short REF-N citation tokens and returns the ref->chunk mapping.
- build_retrieval_context_plain(): Legacy helper used by Ship30/Artifact
  skills that only need the formatted context string.
- is_insufficient_evidence(): Detects when retrieval returned no qualifying results.
"""

from __future__ import annotations

import re
from typing import Any

from app.schemas.retrieval import RetrievalResult


# ---------------------------------------------------------------------------
# System prompt - the grounding contract
# ---------------------------------------------------------------------------

GROUNDING_SYSTEM_PROMPT = """You are the Lenny Growth Assistant.

You answer questions about Lenny Rachitsky's podcast and newsletter using ONLY the retrieved knowledge-base evidence provided to you.

RULES:

1. Use retrieved evidence only.
Never use outside or pretrained knowledge to answer Lenny-specific questions.

2. For every substantive Lenny-specific question, use the retrieve_knowledge tool before answering.

3. CITATIONS ARE REQUIRED.
Every factual claim based on retrieved evidence MUST end with a citation.

The ONLY valid citation format is:
[REF-1]
[REF-2]
[REF-3]

Use only REF-N labels that actually appear in the retrieved evidence.

Example:
"Retention is a major source of sustainable growth. [REF-1]
The source also explains that activation affects conversion. [REF-2]"

IMPORTANT:
- Write the citation exactly as [REF-1], [REF-2], etc.
- Do NOT write the UUID.
- Do NOT write "Source:" as the citation.
- Do NOT invent REF numbers.
- Do NOT answer a knowledge-base question without at least one [REF-N] citation.

4. Stay relevant.
Answer only what the user asked.
Do not add unrelated information from the retrieved chunks.

5. Never fabricate:
- Episode names
- Guest names
- Timestamps
- Quotes
- URLs
- Strategies
- Facts

6. CONFLICTING EVIDENCE.
If retrieved chunks contradict each other, explicitly state the conflict rather than silently choosing one claim.

7. INSUFFICIENT EVIDENCE.
If the retrieved evidence does not contain enough information to answer confidently, respond exactly:

"I don't have enough evidence in the Lenny knowledge base to answer that confidently.
The knowledge base doesn't contain relevant information about this topic."

Do NOT answer from general knowledge in this situation.

8. Clearly distinguish between:
- What the retrieved source directly says
- Your own interpretation or synthesis

9. For general non-Lenny questions, you may use general knowledge, but clearly state that the answer is general knowledge rather than knowledge-base evidence.

10. Keep answers concise and directly relevant to the user's question.

The knowledge base is the source of truth.
Accuracy and traceability are more important than completeness."""


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
# REF-N citation helpers
# ---------------------------------------------------------------------------

REF_CITATION_PATTERN = re.compile(r"\[REF-(\d+)\]")


def make_ref_label(index: int) -> str:
    """Return the short citation token for the given 1-based index."""
    return f"REF-{index}"


# ---------------------------------------------------------------------------
# Context formatting
# ---------------------------------------------------------------------------

def build_retrieval_context(
    results: list[RetrievalResult],
    start_index: int = 1,
) -> tuple[str, dict[str, RetrievalResult]]:
    """Format retrieved chunks for the LLM using short REF-N citation tokens.

    Parameters
    ----------
    results:
        List of retrieved chunks from the Retriever.

    start_index:
        The starting REF number (1-based). Used when the retrieval tool
        is called multiple times in a single turn so that REF numbers
        remain unique and increasing.

    Returns
    -------
    tuple[str, dict[str, RetrievalResult]]
        A 2-tuple containing:
        - The formatted context block for the LLM.
        - A mapping from short reference label to the original
          RetrievalResult object.
    """
    if not results:
        return "", {}

    ref_mapping: dict[str, RetrievalResult] = {}
    lines = ["=== RETRIEVED KNOWLEDGE BASE EVIDENCE ===\n"]

    for offset, result in enumerate(results):
        ref_num = start_index + offset
        ref_label = make_ref_label(ref_num)
        ref_mapping[ref_label] = result

        source_parts = [result.title]

        if result.guest_name:
            source_parts.append(f"feat. {result.guest_name}")

        source_label = " — ".join(source_parts)

        ts_info = ""

        if (
            result.timestamp_start is not None
            and result.timestamp_end is not None
        ):
            ts_info = (
                f" [{result.timestamp_start:.1f}s–"
                f"{result.timestamp_end:.1f}s]"
            )

        lines.append(f"[{ref_label}]")
        lines.append(
            f"Source: {source_label}{ts_info} | "
            f"similarity={result.similarity_score:.3f}"
        )
        lines.append(f"Chunk ID: {result.chunk_id}")
        lines.append(result.content)
        lines.append("")

    lines.append("=== END OF RETRIEVED EVIDENCE ===")

    return "\n".join(lines), ref_mapping


def build_retrieval_context_plain(
    results: list[RetrievalResult],
) -> str:
    """Return only the formatted context string (no mapping).

    This is a convenience wrapper used by callers (Ship30, Artifact) that
    do not perform REF-based citation verification.
    """
    context, _ = build_retrieval_context(results)
    return context


def extract_ref_citations(text: str) -> set[str]:
    """Parse all [REF-N] tokens from model output.

    Returns
    -------
    set[str]
        For example: {"REF-1", "REF-3"}
    """
    return {
        f"REF-{match.group(1)}"
        for match in REF_CITATION_PATTERN.finditer(text)
    }


def is_insufficient_evidence(
    results: list[RetrievalResult],
) -> bool:
    """Return True if retrieval results are empty or below useful threshold.

    Parameters
    ----------
    results:
        Retrieved knowledge-base chunks.

    Returns
    -------
    bool
        True if there is no useful evidence to answer the question.
    """
    return len(results) == 0