"""Pydantic schemas for conversational sessions."""

import uuid
from datetime import datetime

from pydantic import BaseModel

from app.schemas.message import MessageResponse


class SessionResponse(BaseModel):
    """API response for a session (without messages)."""

    id: uuid.UUID
    model_provider: str
    metadata_: dict | None = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class SessionWithMessagesResponse(SessionResponse):
    """API response for a session including its messages."""

    messages: list[MessageResponse] = []
