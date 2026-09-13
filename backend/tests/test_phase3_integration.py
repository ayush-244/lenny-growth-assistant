"""Integration test for Phase 3 (End-to-End Grounded Conversational Core)."""

from unittest.mock import MagicMock
import uuid

import pytest

from app.models.chunk import Chunk
from app.models.transcript import Transcript


@pytest.fixture
def test_data(db_session):
    """Seed the DB with some transcripts and chunks."""
    transcript = Transcript(
        episode_id="ep-999",
        title="Test Episode"
    )
    db_session.add(transcript)
    db_session.flush()
    
    from app.rag.embeddings import DeterministicTestEmbeddingProvider
    provider = DeterministicTestEmbeddingProvider()
    
    # NOTE: DeterministicTestEmbeddingProvider tokenises by whitespace.
    # Punctuation is NOT stripped, so "retention." and "retention" hash to
    # different buckets (cosine similarity = 0).  We use a punctuation-free
    # sentence so the query token "retention" overlaps with the stored token.
    chunk_content = "Lenny says the most important metric is retention"
    chunk = Chunk(
        transcript_id=transcript.id,
        chunk_index=0,
        content=chunk_content,
        embedding=provider.embed(chunk_content),
        timestamp_start=0.0,
        timestamp_end=10.0
    )
    db_session.add(chunk)
    db_session.commit()


def test_end_to_end_conversational_flow(client, db_session, test_data, monkeypatch):
    """Test full flow: Create session, ask question, agent loop."""
    
    # We mock the LLM Provider but KEEP the Orchestrator, SessionService, and Retriever real.
    # The Retriever needs the TestEmbeddingProvider (which our tests already use via monkeypatch in conftest).
    
    mock_provider = MagicMock()
    mock_provider.chat.return_value = MagicMock(
        content="Based on the episode, retention is key.",
        provider="mocked",
        model="mocked"
    )
    
    monkeypatch.setattr(
        "app.agents.orchestrator.get_llm_provider",
        lambda name: mock_provider
    )
    
    from app.rag.embeddings import DeterministicTestEmbeddingProvider
    monkeypatch.setattr(
        "app.rag.embeddings.get_embedding_provider",
        lambda: DeterministicTestEmbeddingProvider()
    )
    
    # The Agent will call provider.chat. We can't easily mock the tool use loop since we mocked the whole provider,
    # but the orchestrator will pass the Retriever tool down.
    # To truly test the flow, let's manually invoke the retriever in our mock to simulate tool execution.
    
    # The DeterministicTestEmbeddingProvider requires sufficient token overlap
    # to exceed RAG_MIN_SIMILARITY=0.35.  Using the exact chunk content as the
    # query guarantees cosine similarity = 1.0 (identical vectors).
    CHUNK_CONTENT = "Lenny says the most important metric is retention"

    def side_effect(messages, system_prompt, tools, tool_executor):
        # Simulate LLM deciding to call a tool; use exact chunk text as query
        # so the deterministic provider gives similarity = 1.0.
        result = tool_executor("retrieve_knowledge", {"query": CHUNK_CONTENT})
        assert "retention" in result

        # Then return the final answer, ensuring we include the chunk ID so it's parsed as grounded!
        chunk_id = db_session.query(Chunk).filter(Chunk.content == CHUNK_CONTENT).first().id
        mock_provider.chat.return_value.content = f"Based on the episode, retention is key. [{chunk_id}]"

        return mock_provider.chat.return_value

    mock_provider.chat.side_effect = side_effect
    
    # 1. Create Session
    resp = client.post("/sessions")
    assert resp.status_code == 201
    session_id = resp.json()["id"]
    
    # 2. Send Message
    msg_resp = client.post(
        f"/sessions/{session_id}/messages",
        json={"content": "What is the most important metric?"}
    )
    assert msg_resp.status_code == 200
    data = msg_resp.json()
    
    assert data["role"] == "assistant"
    assert "Based on the episode, retention is key." in data["content"]
    assert data["grounded"] is True
    assert len(data["citations"]) == 1
    assert data["citations"][0]["title"] == "Test Episode"
