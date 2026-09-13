"""Pydantic schemas for Ship30 essay generation."""

import uuid
from datetime import datetime

from pydantic import BaseModel, Field

from app.schemas.message import CitationSchema, MessageResponse


class EssayCreate(BaseModel):
    """Payload for requesting a Ship30 essay."""

    content: str = Field(
        ...,
        min_length=1,
        max_length=2000,
        description="The essay request. E.g. 'Write a Ship 30 essay about retention.'",
    )


class EssayResponse(MessageResponse):
    """API response for a generated Ship30 essay.

    Extends MessageResponse with Ship30-specific metadata:
    - word_count: Actual word count of the essay prose.
    - generation_attempts: Number of generation attempts (1 or 2).
    - insufficient_evidence: True if retrieval found no supporting content.
    - validation_issues: List of validation failure messages (empty = clean).
    """

    word_count: int = 0
    generation_attempts: int = 1
    insufficient_evidence: bool = False
    validation_issues: list[str] = []
