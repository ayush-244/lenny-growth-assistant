"""Pydantic schemas for Artifact generation and responses."""

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict


class ArtifactCreate(BaseModel):
    """Payload for generating an artifact."""

    request: str
    artifact_type: str  # "markdown" or "html"


class ArtifactResponse(BaseModel):
    """Response containing an artifact."""

    id: uuid.UUID
    session_id: uuid.UUID
    artifact_type: str
    content: str
    request: str
    grounded: bool
    provider: str | None = None
    title: str | None = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
