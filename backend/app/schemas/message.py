"""Pydantic schemas for messages."""

import uuid
from datetime import datetime

from pydantic import BaseModel, Field


class CitationSchema(BaseModel):
    """Citation metadata for a grounded answer."""

    chunk_id: uuid.UUID
    episode_id: str
    title: str
    guest_name: str | None = None
    source_url: str | None = None
    timestamp_start: float | None = None
    timestamp_end: float | None = None


class MessageCreate(BaseModel):
    """Payload for creating a new user message."""

    content: str = Field(..., min_length=1, max_length=10000)


class MessageResponse(BaseModel):
    """API response for a message."""

    id: uuid.UUID
    session_id: uuid.UUID
    role: str
    content: str
    citations: list[CitationSchema] | None = None
    grounded: bool = False
    provider: str | None = None
    created_at: datetime

    model_config = {"from_attributes": True}
