"""Tests for the conversational agent orchestrator."""

from unittest.mock import MagicMock, patch
import uuid

import pytest
from app.agents.orchestrator import GroundedConversationalAgent
from app.llm.base import LLMResponse
from app.schemas.retrieval import RetrievalResult


def test_agent_successful_turn(db_session, monkeypatch):
    """Test a successful agent turn with retrieval and citations."""
    
    # Init agent
    agent = GroundedConversationalAgent(db_session)
    
    from app.schemas.retrieval import RetrievalResponse
    # Mock retriever
    test_chunk_id = uuid.uuid4()
    mock_results = [
        RetrievalResult(
            chunk_id=test_chunk_id,
            transcript_id=uuid.uuid4(),
            chunk_index=0,
            episode_id="ep-123",
            title="Growth",
            content="Retention is key.",
            similarity_score=0.9,
            guest_name=None,
            source_url=None,
            timestamp_start=None,
            timestamp_end=None
        )
    ]
    mock_response = RetrievalResponse(
        query="retention",
        results=mock_results,
        total_found=1,
        threshold_applied=0.35
    )
    agent.retriever.retrieve = MagicMock(return_value=mock_response)

    # Mock LLM Router to return a deterministic provider
    mock_provider = MagicMock()
    def side_effect(messages, system_prompt, tools, tool_executor):
        # Simulate LLM deciding to call a tool
        tool_executor("retrieve_knowledge", {"query": "retention"})
        return LLMResponse(
            content=f"Lenny says retention is key. [{test_chunk_id}]",
            provider="test_provider",
            model="test_model",
            tool_calls_made=1
        )

    mock_provider.chat.side_effect = side_effect

    monkeypatch.setattr(
        "app.agents.orchestrator.get_llm_provider",
        lambda name: mock_provider
    )
    
    # Now call the agent (the mock provider side_effect invokes the tool and returns the response)
    result = agent.answer_question("What is the key to growth?")
    
    assert result["answer"] == f"Lenny says retention is key. [{test_chunk_id}]"
    assert result["grounded"] is True
    assert len(result["citations"]) == 1
    assert result["citations"][0]["episode_id"] == "ep-123"
    assert result["provider"] == "test_provider"


def test_agent_insufficient_evidence(db_session, monkeypatch):
    """Test agent behavior when retriever finds no results."""
    
    mock_provider = MagicMock()
    mock_provider.chat.return_value = LLMResponse(
        content="I don't have enough evidence.",
        provider="test_provider",
        model="test_model"
    )
    
    monkeypatch.setattr(
        "app.agents.orchestrator.get_llm_provider",
        lambda name: mock_provider
    )
    
    agent = GroundedConversationalAgent(db_session)
    
    # Mock retriever returning empty
    from app.schemas.retrieval import RetrievalResponse
    mock_response = RetrievalResponse(
        query="aliens",
        results=[],
        total_found=0,
        threshold_applied=0.35
    )
    agent.retriever.retrieve = MagicMock(return_value=mock_response)
    
    # Simulate LLM tool call
    agent._execute_tool("retrieve_knowledge", {"query": "aliens"})
    
    result = agent.answer_question("Are there aliens?")
    
    assert result["grounded"] is False
    assert len(result["citations"]) == 0
