"""Integration tests for the retrieval layer.

Requirements
------------
- PostgreSQL (Docker) must be running.
- Migrations must be applied (alembic upgrade head).
- No Ollama required — DeterministicTestEmbeddingProvider is used.

These tests seed data using the transaction-rollback db_session fixture,
so no permanent changes are made to the database.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

import pytest

from app.models.chunk import Chunk
from app.models.transcript import Transcript
from app.rag.embeddings import DeterministicTestEmbeddingProvider
from app.rag.retriever import Retriever
from app.schemas.retrieval import RetrievalResponse

pytestmark = pytest.mark.integration


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def make_transcript(db, episode_id: str = "test-ep-001", title: str = "Test Episode") -> Transcript:
    t = Transcript(
        episode_id=episode_id,
        title=title,
        guest_name="Test Guest",
        source_url="https://example.com/test",
        ingested_at=datetime.now(timezone.utc),
    )
    db.add(t)
    db.flush()
    return t


def make_chunk(
    db,
    transcript: Transcript,
    content: str,
    chunk_index: int,
    embedding: list[float],
    ts_start: float = 0.0,
    ts_end: float = 10.0,
) -> Chunk:
    c = Chunk(
        transcript_id=transcript.id,
        content=content,
        chunk_index=chunk_index,
        timestamp_start=ts_start,
        timestamp_end=ts_end,
        embedding=embedding,
    )
    db.add(c)
    db.flush()
    return c


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture()
def provider():
    return DeterministicTestEmbeddingProvider()


@pytest.fixture()
def seeded_db(db_session, provider):
    """Seed the database with pricing and hiring chunks for retrieval tests."""
    transcript = make_transcript(db_session, "retrieval-test-001", "Retrieval Test Episode")

    pricing_text = "pricing strategy revenue model SaaS pricing tiers"
    hiring_text = "hiring manager interview process onboarding new employees"
    growth_text = "growth loop acquisition retention product-led growth strategy"

    chunks = [
        make_chunk(
            db_session, transcript,
            content=pricing_text,
            chunk_index=0,
            embedding=provider.embed(pricing_text),
            ts_start=0.0, ts_end=30.0,
        ),
        make_chunk(
            db_session, transcript,
            content=hiring_text,
            chunk_index=1,
            embedding=provider.embed(hiring_text),
            ts_start=30.0, ts_end=60.0,
        ),
        make_chunk(
            db_session, transcript,
            content=growth_text,
            chunk_index=2,
            embedding=provider.embed(growth_text),
            ts_start=60.0, ts_end=90.0,
        ),
    ]
    return transcript, chunks


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

class TestRetrieval:
    def test_retrieve_returns_response_object(self, db_session, seeded_db, provider):
        retriever = Retriever(provider)
        response = retriever.retrieve("pricing strategy", db_session, top_k=5, min_similarity=0.0)
        assert isinstance(response, RetrievalResponse)

    def test_retrieve_top_k_limits_results(self, db_session, seeded_db, provider):
        retriever = Retriever(provider)
        response = retriever.retrieve("growth strategy", db_session, top_k=1, min_similarity=0.0)
        assert len(response.results) <= 1

    def test_results_ordered_by_similarity_descending(self, db_session, seeded_db, provider):
        retriever = Retriever(provider)
        response = retriever.retrieve("pricing strategy", db_session, top_k=5, min_similarity=0.0)
        scores = [r.similarity_score for r in response.results]
        assert scores == sorted(scores, reverse=True), "Results not ordered by similarity"

    def test_pricing_query_ranks_pricing_chunk_highest(self, db_session, seeded_db, provider):
        """Pricing-related query should rank the pricing chunk above the hiring chunk."""
        retriever = Retriever(provider)
        response = retriever.retrieve("pricing strategy", db_session, top_k=5, min_similarity=0.0)
        assert response.has_results
        top_result = response.results[0]
        assert "pricing" in top_result.content.lower(), (
            f"Expected pricing chunk at top, got: {top_result.content!r}"
        )

    def test_citation_metadata_is_present(self, db_session, seeded_db, provider):
        transcript, _ = seeded_db
        retriever = Retriever(provider)
        response = retriever.retrieve("pricing", db_session, top_k=5, min_similarity=0.0)
        assert response.has_results
        result = response.results[0]
        assert result.episode_id == transcript.episode_id
        assert result.title == transcript.title
        assert result.guest_name == transcript.guest_name
        assert result.source_url == transcript.source_url
        assert result.chunk_id is not None
        assert result.transcript_id == transcript.id

    def test_timestamp_metadata_preserved(self, db_session, seeded_db, provider):
        retriever = Retriever(provider)
        response = retriever.retrieve("pricing strategy", db_session, top_k=5, min_similarity=0.0)
        assert response.has_results
        result = response.results[0]
        assert result.timestamp_start is not None
        assert result.timestamp_end is not None

    def test_similarity_threshold_filters_weak_results(self, db_session, seeded_db, provider):
        """With a very high threshold, no results should be returned."""
        retriever = Retriever(provider)
        response = retriever.retrieve(
            "completely unrelated topic xyz",
            db_session,
            top_k=5,
            min_similarity=0.999,  # unreachably high
        )
        assert not response.has_results
        assert response.total_found == 0

    def test_threshold_applied_field_is_set(self, db_session, seeded_db, provider):
        retriever = Retriever(provider)
        response = retriever.retrieve("test", db_session, top_k=5, min_similarity=0.5)
        assert response.threshold_applied == 0.5

    def test_empty_retrieval_explicit_empty_response(self, db_session, provider):
        """Retrieval against an empty database returns an explicit empty response."""
        retriever = Retriever(provider)
        response = retriever.retrieve("anything", db_session, top_k=5, min_similarity=0.0)
        assert isinstance(response, RetrievalResponse)
        assert response.results == []
        assert not response.has_results

    def test_query_text_preserved_in_response(self, db_session, seeded_db, provider):
        retriever = Retriever(provider)
        query = "my specific query text"
        response = retriever.retrieve(query, db_session, top_k=5, min_similarity=0.0)
        assert response.query == query
