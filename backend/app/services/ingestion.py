"""Transcript ingestion service.

Idempotency strategy
--------------------
If an episode with the same episode_id already exists in the database,
we delete its chunks and re-insert them. The transcript metadata record
is updated in place. This ensures that re-running ingestion on the same
fixture does not accumulate duplicate chunks.

Logging
-------
The service logs the operation, episode_id, chunk count, and the
embedding provider name at INFO level. Individual chunk details are
logged at DEBUG level.
"""

from __future__ import annotations

import logging
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.models.chunk import Chunk
from app.models.transcript import Transcript
from app.rag.chunker import TranscriptChunker
from app.rag.embeddings import EmbeddingProvider

logger = logging.getLogger(__name__)


@dataclass
class IngestionResult:
    """Result summary from a single ingestion operation."""

    episode_id: str
    transcript_id: uuid.UUID
    chunks_created: int
    was_update: bool  # True if the episode already existed and was re-ingested


class IngestionService:
    """Ingests transcript fixtures into the knowledge base.

    Responsibilities
    ----------------
    - Parse fixture data.
    - Create or update the Transcript record.
    - Chunk the transcript using TranscriptChunker.
    - Embed each chunk using the provided EmbeddingProvider.
    - Persist Chunk records.
    - Guarantee idempotency for the same episode_id.
    """

    def __init__(
        self,
        chunker: TranscriptChunker | None = None,
    ) -> None:
        self._chunker = chunker or TranscriptChunker()

    def ingest_episode(
        self,
        fixture: dict,
        db: Session,
        embedding_provider: EmbeddingProvider,
    ) -> IngestionResult:
        """Ingest a single episode fixture into the database.

        Parameters
        ----------
        fixture:
            Parsed JSON fixture dict. Must contain: episode_id, title, segments.
            Optional: guest_name, source_url.
        db:
            Active SQLAlchemy Session. Caller is responsible for commit/rollback.
        embedding_provider:
            Provider used to generate embeddings. Must be real (OllamaEmbeddingProvider)
            for production ingestion. Test ingestion may use DeterministicTestEmbeddingProvider.

        Returns
        -------
        IngestionResult

        Raises
        ------
        EmbeddingError
            If the embedding provider is unavailable or returns invalid data.
        ValueError
            If required fixture fields are missing.
        """
        episode_id: str = fixture.get("episode_id", "").strip()
        title: str = fixture.get("title", "").strip()
        segments: list[dict] = fixture.get("segments", [])

        if not episode_id:
            raise ValueError("Fixture missing required field: episode_id")
        if not title:
            raise ValueError("Fixture missing required field: title")

        logger.info(
            "Starting ingestion episode_id=%r title=%r segments=%d",
            episode_id,
            title,
            len(segments),
        )

        # --- Idempotency: check for existing transcript ---
        existing: Transcript | None = (
            db.query(Transcript).filter_by(episode_id=episode_id).first()
        )
        was_update = existing is not None

        if existing is not None:
            logger.info(
                "Episode %r already exists (id=%s). Deleting existing chunks for re-ingestion.",
                episode_id,
                existing.id,
            )
            # Delete existing chunks (cascade handles FK; explicit for clarity)
            db.query(Chunk).filter_by(transcript_id=existing.id).delete()
            transcript = existing
            transcript.title = title
            transcript.guest_name = fixture.get("guest_name")
            transcript.source_url = fixture.get("source_url")
            transcript.ingested_at = datetime.now(timezone.utc)
        else:
            transcript = Transcript(
                episode_id=episode_id,
                title=title,
                guest_name=fixture.get("guest_name"),
                source_url=fixture.get("source_url"),
                ingested_at=datetime.now(timezone.utc),
            )
            db.add(transcript)
            db.flush()  # Populate transcript.id before inserting chunks

        # --- Chunk the transcript ---
        chunk_data_list = self._chunker.chunk(segments)
        logger.info(
            "Chunked episode_id=%r into %d chunks",
            episode_id,
            len(chunk_data_list),
        )

        # --- Embed and persist each chunk ---
        chunks_created = 0
        for chunk_data in chunk_data_list:
            logger.debug(
                "Embedding chunk_index=%d episode_id=%r",
                chunk_data.chunk_index,
                episode_id,
            )
            embedding = embedding_provider.embed(chunk_data.content)

            chunk = Chunk(
                transcript_id=transcript.id,
                content=chunk_data.content,
                chunk_index=chunk_data.chunk_index,
                timestamp_start=chunk_data.timestamp_start,
                timestamp_end=chunk_data.timestamp_end,
                embedding=embedding,
            )
            db.add(chunk)
            chunks_created += 1

        db.flush()

        logger.info(
            "Ingestion complete episode_id=%r transcript_id=%s "
            "chunks_created=%d was_update=%s",
            episode_id,
            transcript.id,
            chunks_created,
            was_update,
        )

        return IngestionResult(
            episode_id=episode_id,
            transcript_id=transcript.id,
            chunks_created=chunks_created,
            was_update=was_update,
        )
