"""Pydantic schemas for retrieval responses.

These schemas are the API contract for retrieval results. They are kept
separate from ORM models to avoid leaking database internals.

RetrievalResult contains all citation-relevant metadata so the agent layer
can construct traceable citations without querying the database again.
"""

from __future__ import annotations

import uuid

from pydantic import BaseModel, Field


class RetrievalResult(BaseModel):
    """A single retrieved transcript chunk with citation metadata."""

    chunk_id: uuid.UUID = Field(description="Primary key of the chunk record")
    transcript_id: uuid.UUID = Field(description="Primary key of the parent transcript")
    content: str = Field(description="The text content of this chunk")
    similarity_score: float = Field(
        description="Cosine similarity score between query and chunk (0–1, higher is better)"
    )
    # Citation metadata
    episode_id: str = Field(description="External episode identifier for citations")
    title: str = Field(description="Episode/article title")
    guest_name: str | None = Field(default=None, description="Guest name if applicable")
    source_url: str | None = Field(default=None, description="Source URL for citation")
    # Position metadata
    timestamp_start: float | None = Field(
        default=None, description="Start timestamp in seconds (if available)"
    )
    timestamp_end: float | None = Field(
        default=None, description="End timestamp in seconds (if available)"
    )
    chunk_index: int = Field(description="Zero-based chunk index within the episode")


class RetrievalResponse(BaseModel):
    """Container for retrieval results with query context."""

    query: str = Field(description="The original query text")
    results: list[RetrievalResult] = Field(
        default_factory=list,
        description="Retrieved chunks ordered by descending similarity",
    )
    total_found: int = Field(
        description="Number of results that met the similarity threshold"
    )
    threshold_applied: float = Field(
        description="Minimum similarity threshold used to filter results"
    )

    @property
    def has_results(self) -> bool:
        """True if at least one result met the similarity threshold."""
        return len(self.results) > 0
