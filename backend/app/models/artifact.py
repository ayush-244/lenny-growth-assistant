"""Artifact database model.

An Artifact is a structured document (Markdown or HTML/CSS) generated from
a session conversational context, grounded in retrieved evidence.

Artifacts are owned by a Session and isolated per-session.
"""

import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, String, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.database import Base


class Artifact(Base):
    """A generated artifact owned by a session."""

    __tablename__ = "artifacts"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    session_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("sessions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    #: "markdown" or "html"
    artifact_type: Mapped[str] = mapped_column(String(20), nullable=False)
    #: The generated content (Markdown source or full HTML document)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    #: Original user request that produced this artifact
    request: Mapped[str] = mapped_column(Text, nullable=False)
    #: Whether the content is grounded in retrieved evidence
    grounded: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    #: Provider that generated the artifact
    provider: Mapped[str] = mapped_column(String(50), nullable=True)
    #: Brief title derived from the request (for display)
    title: Mapped[str] = mapped_column(String(200), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
        index=True,
    )

    session: Mapped["Session"] = relationship(  # type: ignore[name-defined] # noqa: F821
        "Session",
        back_populates="artifacts",
    )
