import uuid
from datetime import datetime, timezone

from sqlalchemy import DateTime, String, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.database import Base


class Transcript(Base):
    """Represents a podcast episode or newsletter entry.

    Each Transcript is the top-level record for a piece of Lenny content.
    Chunks are derived from a Transcript and reference it via foreign key.
    """

    __tablename__ = "transcripts"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    episode_id: Mapped[str] = mapped_column(
        String,
        unique=True,
        index=True,
        nullable=False,
        comment="External identifier for the episode (e.g. 'ep-123')",
    )
    title: Mapped[str] = mapped_column(String, nullable=False)
    guest_name: Mapped[str | None] = mapped_column(String, nullable=True)
    source_url: Mapped[str | None] = mapped_column(String, nullable=True)
    ingested_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    # Relationship — allows chunk.transcript to resolve citation metadata
    chunks: Mapped[list["Chunk"]] = relationship(  # type: ignore[name-defined]  # noqa: F821
        "Chunk",
        back_populates="transcript",
        cascade="all, delete-orphan",
    )

    def __repr__(self) -> str:
        return f"<Transcript id={self.id} episode_id={self.episode_id!r}>"
