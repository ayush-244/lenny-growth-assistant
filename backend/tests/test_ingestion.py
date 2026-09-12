"""Integration tests for the ingestion service.

Requirements
------------
- PostgreSQL (Docker) must be running.
- Migrations must be applied (alembic upgrade head).
- No Ollama required — DeterministicTestEmbeddingProvider is used.
"""

from __future__ import annotations

import pytest

from app.models.chunk import Chunk
from app.models.transcript import Transcript
from app.services.ingestion import IngestionService

pytestmark = pytest.mark.integration


class TestIngestionService:
    def test_fixture_loads(self, sample_fixture):
        assert "episode_id" in sample_fixture
        assert "segments" in sample_fixture
        assert len(sample_fixture["segments"]) > 0

    def test_transcript_is_created(self, db_session, sample_fixture, deterministic_provider):
        service = IngestionService()
        result = service.ingest_episode(sample_fixture, db_session, deterministic_provider)
        transcript = db_session.query(Transcript).filter_by(
            episode_id=sample_fixture["episode_id"]
        ).first()
        assert transcript is not None
        assert transcript.title == sample_fixture["title"]
        assert transcript.guest_name == sample_fixture.get("guest_name")

    def test_chunks_are_created(self, db_session, sample_fixture, deterministic_provider):
        service = IngestionService()
        result = service.ingest_episode(sample_fixture, db_session, deterministic_provider)
        assert result.chunks_created > 0
        chunks = db_session.query(Chunk).filter_by(
            transcript_id=result.transcript_id
        ).all()
        assert len(chunks) == result.chunks_created

    def test_embeddings_are_stored(self, db_session, sample_fixture, deterministic_provider):
        service = IngestionService()
        result = service.ingest_episode(sample_fixture, db_session, deterministic_provider)
        chunks = db_session.query(Chunk).filter_by(
            transcript_id=result.transcript_id
        ).all()
        for chunk in chunks:
            assert chunk.embedding is not None
            assert len(chunk.embedding) == 768

    def test_ingestion_is_idempotent(self, db_session, sample_fixture, deterministic_provider):
        """Running ingestion twice should not create duplicate transcripts or chunks."""
        service = IngestionService()

        result1 = service.ingest_episode(sample_fixture, db_session, deterministic_provider)
        assert not result1.was_update

        result2 = service.ingest_episode(sample_fixture, db_session, deterministic_provider)
        assert result2.was_update

        # Only one transcript record should exist
        count = (
            db_session.query(Transcript)
            .filter_by(episode_id=sample_fixture["episode_id"])
            .count()
        )
        assert count == 1

        # Chunk count should be the same after re-ingestion
        assert result1.chunks_created == result2.chunks_created

    def test_chunk_indices_are_sequential(self, db_session, sample_fixture, deterministic_provider):
        service = IngestionService()
        result = service.ingest_episode(sample_fixture, db_session, deterministic_provider)
        chunks = (
            db_session.query(Chunk)
            .filter_by(transcript_id=result.transcript_id)
            .order_by(Chunk.chunk_index)
            .all()
        )
        for i, chunk in enumerate(chunks):
            assert chunk.chunk_index == i

    def test_missing_episode_id_raises(self, db_session, deterministic_provider):
        service = IngestionService()
        bad_fixture = {"title": "No ID Episode", "segments": []}
        with pytest.raises(ValueError, match="episode_id"):
            service.ingest_episode(bad_fixture, db_session, deterministic_provider)

    def test_missing_title_raises(self, db_session, deterministic_provider):
        service = IngestionService()
        bad_fixture = {"episode_id": "no-title-001", "segments": []}
        with pytest.raises(ValueError, match="title"):
            service.ingest_episode(bad_fixture, db_session, deterministic_provider)
