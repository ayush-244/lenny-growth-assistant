"""Grounding policy for the Lenny Growth Assistant.

This module defines:
- GROUNDING_SYSTEM_PROMPT: The strict system instruction given to the LLM.
- RETRIEVE_KNOWLEDGE_TOOL: Tool definition for the retrieval capability.
- build_retrieval_context(): Formats retrieved chunks for the LLM with
  short REF-N citation tokens and returns the ref->chunk mapping.
- build_retrieval_context_plain(): Helper used by Ship30/Artifact skills.
- is_insufficient_evidence(): Detects when retrieval returned no results.
"""

from __future__ import annotations

import re

from app.schemas.retrieval import RetrievalResult


# ---------------------------------------------------------------------------
# System prompt
# ---------------------------------------------------------------------------

GROUNDING_SYSTEM_PROMPT = """You are the Lenny Growth Assistant.

Your job is to answer questions about Lenny Rachitsky using the retrieved
knowledge-base evidence.

FOLLOW THESE RULES EXACTLY.

1. RETRIEVE FIRST

For questions about Lenny, his podcast, his newsletter, or the knowledge
base, use the retrieved evidence provided to you. If no evidence is provided,
do not answer from outside knowledge.

2. USE ONLY RETRIEVED EVIDENCE

After retrieval, use only the information contained in the retrieved evidence.

Do not use outside knowledge.
Do not rely on your pretrained knowledge.
Do not invent missing information.

3. CITATIONS ARE REQUIRED

If the retrieved evidence answers the user's question, give a concise answer.

Every factual claim based on the retrieved evidence MUST have a citation.

A citation must use EXACTLY this format:

[REF-1]

or:

[REF-2]

or:

[REF-3]

Use only REF numbers that are explicitly present in the retrieved evidence.

Example:

"Retention supports sustainable growth because it helps create
compounding growth over time. [REF-1]"

Another example:

"One approach discussed is value-based pricing. [REF-2]
Usage-based pricing is also discussed. [REF-3]"

IMPORTANT:
- Always write the citation exactly as [REF-N].
- Do not write the UUID.
- Do not write "Source:" as a citation.
- Do not invent REF numbers.
- Do not use a citation that is not present in the retrieved evidence.
- If the evidence answers the question, include at least one valid citation.

4. INSUFFICIENT EVIDENCE

If the retrieved evidence does not answer the question, respond exactly:

"I don't have enough evidence in the Lenny knowledge base to answer that confidently.
The knowledge base doesn't contain relevant information about this topic."

Do not answer from general knowledge.

5. NO FABRICATION

Never invent:
- facts
- quotes
- episode names
- guest names
- timestamps
- URLs
- strategies
- frameworks
- REF numbers

6. RELEVANCE

Answer only the question asked.

Do not use unrelated information from the retrieved chunks.

7. SOURCE VS INTERPRETATION

Clearly distinguish what the source directly says from your own synthesis.

If you make a synthesis from multiple retrieved chunks, cite the relevant chunks.

8. CONFLICTS

If retrieved evidence contains conflicting information, mention the conflict
instead of silently choosing one version.

9. GENERAL QUESTIONS

For questions that are clearly not about Lenny or the knowledge base, general
knowledge may be used. Do not present general knowledge as retrieved evidence.

10. RESPONSE STYLE

Keep answers concise, useful, and easy to read.

The knowledge base is the source of truth.
Accuracy and traceability are more important than completeness."""


# ---------------------------------------------------------------------------
# Retrieval tool definitions
# ---------------------------------------------------------------------------

RETRIEVE_KNOWLEDGE_TOOL_ANTHROPIC = {
    "name": "retrieve_knowledge",
    "description": (
        "Retrieve relevant transcript chunks from the Lenny Growth Assistant "
        "knowledge base. Use this tool for any question about Lenny's podcast "
        "content, strategies, frameworks, or specific episodes. Always call "
        "this before answering knowledge-base questions."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "query": {
                "type": "string",
                "description": (
                    "Natural-language search query describing the information "
                    "needed from the knowledge base."
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
            "Retrieve relevant transcript chunks from the Lenny Growth "
            "Assistant knowledge base. Use this for any question about "
            "Lenny's podcast content, strategies, or frameworks."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": (
                        "Natural-language search query for knowledge-base "
                        "content."
                    ),
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
    """Return the short citation token for a 1-based reference index."""
    return f"REF-{index}"


def extract_ref_citations(text: str) -> set[str]:
    """Extract [REF-N] citation tokens from model output."""
    return {
        f"REF-{match.group(1)}"
        for match in REF_CITATION_PATTERN.finditer(text)
    }


# ---------------------------------------------------------------------------
# Retrieval context formatting
# ---------------------------------------------------------------------------

def build_retrieval_context(
    results: list[RetrievalResult],
    start_index: int = 1,
) -> tuple[str, dict[str, RetrievalResult]]:
    """Format retrieved chunks with short REF-N labels.

    Returns:
        A tuple containing:
        - formatted evidence for the LLM
        - mapping from REF-N to the original retrieval result
    """

    if not results:
        return "", {}

    ref_mapping: dict[str, RetrievalResult] = {}

    lines = [
        "=== RETRIEVED KNOWLEDGE BASE EVIDENCE ===",
        "",
        "IMPORTANT: Use the REF-N labels below when citing evidence.",
        "Only these REF-N labels are valid.",
        "",
    ]

    for offset, result in enumerate(results):
        ref_num = start_index + offset
        ref_label = make_ref_label(ref_num)

        ref_mapping[ref_label] = result

        source_parts = [result.title]

        if result.guest_name:
            source_parts.append(f"feat. {result.guest_name}")

        source_label = " — ".join(source_parts)

        timestamp = ""

        if (
            result.timestamp_start is not None
            and result.timestamp_end is not None
        ):
            timestamp = (
                f" [{result.timestamp_start:.1f}s–"
                f"{result.timestamp_end:.1f}s]"
            )

        lines.append(f"[{ref_label}]")
        lines.append(
            f"Source: {source_label}{timestamp}"
        )
        lines.append(f"Chunk ID: {result.chunk_id}")
        lines.append("Evidence:")
        lines.append(result.content)
        lines.append("")

    lines.extend(
        [
            "=== END OF RETRIEVED EVIDENCE ===",
            "",
            "Remember: if the evidence answers the question, cite it using "
            "one or more valid [REF-N] labels.",
        ]
    )

    return "\n".join(lines), ref_mapping


def build_retrieval_context_plain(
    results: list[RetrievalResult],
) -> str:
    """Return formatted retrieval context without the mapping."""
    context, _ = build_retrieval_context(results)
    return context


# ---------------------------------------------------------------------------
# Evidence helper
# ---------------------------------------------------------------------------

def is_insufficient_evidence(
    results: list[RetrievalResult],
) -> bool:
    """Return True when retrieval returned no qualifying evidence."""
    return len(results) == 0