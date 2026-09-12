"""Session service for managing conversational state."""

import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session as DbSession

from app.core.config import settings
from app.models.message import Message
from app.models.session import Session


class SessionNotFoundError(Exception):
    """Raised when a session ID does not exist."""


class SessionService:
    """Manages conversations and message persistence."""

    def __init__(self, db_session: DbSession) -> None:
        self.db = db_session

    def create_session(self, metadata: dict | None = None) -> Session:
        """Create a new session."""
        session = Session(
            model_provider=settings.model_provider,
            metadata_=metadata or {},
        )
        self.db.add(session)
        self.db.commit()
        self.db.refresh(session)
        return session

    def get_session(self, session_id: uuid.UUID) -> Session:
        """Retrieve a session by ID."""
        session = self.db.get(Session, session_id)
        if not session:
            raise SessionNotFoundError(f"Session {session_id} not found")
        return session

    def get_recent_history(self, session_id: uuid.UUID) -> list[dict[str, str]]:
        """Retrieve recent conversation history formatted for the LLM.

        Parameters
        ----------
        session_id:
            The session ID.

        Returns
        -------
        list[dict]
            List of {"role": "...", "content": "..."} dicts.
            Limited to settings.conversation_window.
        """
        stmt = (
            select(Message)
            .where(Message.session_id == session_id)
            .order_by(Message.created_at.desc())
            .limit(settings.conversation_window)
        )
        recent_messages = self.db.execute(stmt).scalars().all()

        # Reverse so they are in chronological order
        history = []
        for msg in reversed(recent_messages):
            history.append({
                "role": msg.role,
                "content": msg.content,
            })
        return history

    def add_user_message(self, session_id: uuid.UUID, content: str) -> Message:
        """Persist a user message."""
        self.get_session(session_id)  # Validate session exists
        msg = Message(
            session_id=session_id,
            role="user",
            content=content,
        )
        self.db.add(msg)
        self.db.commit()
        self.db.refresh(msg)
        return msg

    def add_assistant_message(
        self,
        session_id: uuid.UUID,
        content: str,
        citations: list[dict] | None = None,
        grounded: bool = False,
        provider: str | None = None,
    ) -> Message:
        """Persist an assistant message with grounding metadata."""
        self.get_session(session_id)  # Validate session exists
        msg = Message(
            session_id=session_id,
            role="assistant",
            content=content,
            citations=citations or [],
            grounded=grounded,
            provider=provider,
        )
        self.db.add(msg)
        self.db.commit()
        self.db.refresh(msg)
        return msg
