"""Integration test for Phase 3 (End-to-End Grounded Conversational Core)."""

from unittest.mock import MagicMock
import uuid

import pytest

from app.models.chunk import Chunk
from app.models.transcript import Transcript
from app.schemas.retrieval import RetrievalResponse, RetrievalResult


@pytest.fixture
def test_data(db_session):
    """Seed the DB with a transcript and chunk."""

    transcript = Transcript(
        episode_id="ep-999",
        title="Test Episode",
    )

    db_session.add(transcript)
    db_session.flush()

    from app.rag.embeddings import DeterministicTestEmbeddingProvider

    provider = DeterministicTestEmbeddingProvider()

    chunk_content = "Lenny says the most important metric is retention"

    chunk = Chunk(
        transcript_id=transcript.id,
        chunk_index=0,
        content=chunk_content,
        embedding=provider.embed(chunk_content),
        timestamp_start=0.0,
        timestamp_end=10.0,
    )

    db_session.add(chunk)
    db_session.commit()


def test_end_to_end_conversational_flow(
    client,
    db_session,
    test_data,
    monkeypatch,
):
    """Test full flow: create session, retrieve evidence, generate answer."""

    mock_provider = MagicMock()

    mock_provider.chat.return_value = MagicMock(
        content="Based on the episode, retention is key. [REF-1]",
        provider="mocked",
        model="mocked",
    )

    monkeypatch.setattr(
        "app.agents.orchestrator.get_llm_provider",
        lambda name: mock_provider,
    )

    test_chunk_id = uuid.uuid4()

    mock_retrieval = RetrievalResponse(
        query="What is the most important metric?",
        results=[
            RetrievalResult(
                chunk_id=test_chunk_id,
                transcript_id=uuid.uuid4(),
                chunk_index=0,
                episode_id="ep-999",
                title="Test Episode",
                content="Lenny says the most important metric is retention",
                similarity_score=1.0,
                guest_name=None,
                source_url=None,
                timestamp_start=0.0,
                timestamp_end=10.0,
            )
        ],
        total_found=1,
        threshold_applied=0.35,
    )

    monkeypatch.setattr(
        "app.agents.orchestrator.Retriever.retrieve",
        lambda self, **kwargs: mock_retrieval,
    )

    # 1. Create session.
    resp = client.post("/sessions")

    assert resp.status_code == 201

    session_id = resp.json()["id"]

    # 2. Send message.
    msg_resp = client.post(
        f"/sessions/{session_id}/messages",
        json={
            "content": "What is the most important metric?"
        },
    )

    assert msg_resp.status_code == 200

    data = msg_resp.json()

    # 3. Validate assistant response.
    assert data["role"] == "assistant"

    assert (
        data["content"]
        == "Based on the episode, retention is key. [REF-1]"
    )

    assert data["grounded"] is True

    # 4. Validate citation.
    assert len(data["citations"]) == 1

    assert data["citations"][0]["title"] == "Test Episode"

    assert data["citations"][0]["episode_id"] == "ep-999"