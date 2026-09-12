import uuid
from datetime import datetime, timezone

from pgvector.sqlalchemy import Vector
from sqlalchemy import DateTime, Float, ForeignKey, Index, Integer, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.database import Base

# Embedding dimension must match EMBEDDING_DIMENSION in config.
# This constant is used in both the model and the migration.
EMBEDDING_DIM = 768


class Chunk(Base):
    """A single content chunk derived from a Transcript.

    Each chunk contains a slice of transcript text, its position metadata,
    optional timestamp boundaries, and a 768-dimensional vector embedding
    for semantic retrieval via pgvector cosine similarity search.
    """

    __tablename__ = "chunks"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    transcript_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("transcripts.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    content: Mapped[str] = mapped_column(Text, nullable=False)
    chunk_index: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    timestamp_start: Mapped[float | None] = mapped_column(Float, nullable=True)
    timestamp_end: Mapped[float | None] = mapped_column(Float, nullable=True)
    embedding: Mapped[list[float]] = mapped_column(
        Vector(EMBEDDING_DIM),
        nullable=False,
        comment="768-dimensional vector embedding (nomic-embed-text via Ollama)",
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    # Relationship — allows chunk.transcript to resolve full citation metadata
    transcript: Mapped["Transcript"] = relationship(  # type: ignore[name-defined]  # noqa: F821
        "Transcript",
        back_populates="chunks",
    )

    # Composite index for deterministic ordering within a transcript
    __table_args__ = (
        Index("ix_chunks_transcript_chunk", "transcript_id", "chunk_index"),
    )

    def __repr__(self) -> str:
        return (
            f"<Chunk id={self.id} transcript_id={self.transcript_id} "
            f"chunk_index={self.chunk_index}>"
        )
