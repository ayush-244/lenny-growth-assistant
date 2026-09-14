"""Tests for the conversational agent orchestrator."""

from unittest.mock import MagicMock
import uuid

from app.agents.orchestrator import GroundedConversationalAgent
from app.llm.base import LLMResponse
from app.schemas.retrieval import RetrievalResponse, RetrievalResult


def test_agent_successful_turn(db_session, monkeypatch):
    """Test a successful agent turn with retrieval and citations."""

    agent = GroundedConversationalAgent(db_session)

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
            timestamp_end=None,
        )
    ]

    mock_response = RetrievalResponse(
        query="retention",
        results=mock_results,
        total_found=1,
        threshold_applied=0.35,
    )

    agent.retriever.retrieve = MagicMock(return_value=mock_response)

    mock_provider = MagicMock()

    def side_effect(messages, system_prompt, tools, tool_executor):
        return LLMResponse(
            content="Lenny says retention is key. [REF-1]",
            provider="test_provider",
            model="test_model",
            tool_calls_made=0,
        )

    mock_provider.chat.side_effect = side_effect

    monkeypatch.setattr(
        "app.agents.orchestrator.get_llm_provider",
        lambda name: mock_provider,
    )

    result = agent.answer_question("What is the key to growth?")

    assert result["answer"] == "Lenny says retention is key. [REF-1]"
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
        model="test_model",
    )

    monkeypatch.setattr(
        "app.agents.orchestrator.get_llm_provider",
        lambda name: mock_provider,
    )

    agent = GroundedConversationalAgent(db_session)

    mock_response = RetrievalResponse(
        query="aliens",
        results=[],
        total_found=0,
        threshold_applied=0.35,
    )

    agent.retriever.retrieve = MagicMock(return_value=mock_response)

    result = agent.answer_question("Are there aliens?")

    assert result["grounded"] is False
    assert len(result["citations"]) == 0


def test_agent_uses_explicit_session_provider(db_session, monkeypatch):
    """An existing conversation's provider must override MODEL_PROVIDER."""

    captured_provider: list[str] = []

    mock_provider = MagicMock()

    mock_provider.chat.return_value = LLMResponse(
        content="No citation",
        provider="anthropic",
        model="test-model",
    )

    def get_provider(name: str):
        captured_provider.append(name)
        return mock_provider

    monkeypatch.setattr(
        "app.agents.orchestrator.get_llm_provider",
        get_provider,
    )

    agent = GroundedConversationalAgent(db_session)

    agent.answer_question(
        "Question",
        provider_name="anthropic",
    )

    assert captured_provider == ["anthropic"]


def test_context_formatting_and_edge_cases(db_session, monkeypatch):
    """Test grounding context formatting and citation edge cases."""

    from app.agents.grounding import build_retrieval_context

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
            guest_name="Guest Name",
            source_url=None,
            timestamp_start=None,
            timestamp_end=None,
        )
    ]

    context, mapping = build_retrieval_context(mock_results)

    assert "[REF-1]" in context
    assert "[REF-1 |" not in context
    assert "Source: Growth — feat. Guest Name" in context
    assert f"Chunk ID: {test_chunk_id}" in context
    assert mapping["REF-1"] == mock_results[0]

    agent = GroundedConversationalAgent(db_session)

    mock_response = RetrievalResponse(
        query="retention",
        results=mock_results,
        total_found=1,
        threshold_applied=0.35,
    )

    agent.retriever.retrieve = MagicMock(return_value=mock_response)

    def _test_with_response(
        llm_output: str,
        expected_grounded: bool,
    ):
        mock_provider = MagicMock()

        def side_effect(messages, system_prompt, tools, tool_executor):
            return LLMResponse(
                content=llm_output,
                provider="test",
                model="test",
                tool_calls_made=0,
            )

        mock_provider.chat.side_effect = side_effect

        monkeypatch.setattr(
            "app.agents.orchestrator.get_llm_provider",
            lambda name: mock_provider,
        )

        result = agent.answer_question("test")

        assert result["grounded"] == expected_grounded

    # G. No citation
    _test_with_response(
        "Retention supports sustainable growth.",
        False,
    )

    # H. Invalid citation
    _test_with_response(
        "Retention supports sustainable growth. [REF-999]",
        False,
    )

    # I. Fake metadata inside citation brackets
    _test_with_response(
        "Retention supports sustainable growth. [REF-1 | fake metadata]",
        False,
    )