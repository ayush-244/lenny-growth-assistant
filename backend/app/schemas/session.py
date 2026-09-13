"""Pydantic schemas for conversational sessions."""

import uuid
from datetime import datetime

from enum import Enum

from pydantic import BaseModel

from app.schemas.message import MessageResponse


class ProviderName(str, Enum):
    OLLAMA = "ollama"
    ANTHROPIC = "anthropic"


class ProviderUpdateRequest(BaseModel):
    provider: ProviderName


class ProviderUpdateResponse(BaseModel):
    session_id: uuid.UUID
    provider: ProviderName
    model: str


class SessionResponse(BaseModel):
    """API response for a session (without messages)."""

    id: uuid.UUID
    model_provider: str
    model: str
    metadata_: dict | None = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class SessionWithMessagesResponse(SessionResponse):
    """API response for a session including its messages."""

    messages: list[MessageResponse] = []
