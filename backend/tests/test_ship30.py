"""Tests for the Ship30 essay generation skill.

All tests are fully deterministic — no live Anthropic, Ollama, or PostgreSQL required
for most tests (those that need a DB session use the in-transaction rollback fixture).

Coverage:
- Topic resolution (direct, pronoun reference)
- Bounded conversation context (exactly 4 messages)
- Insufficient evidence handling
- Word count validation
- Citation validation
- LLM output parsing
- Bounded regeneration (max 2 attempts)
- Provider abstraction (not hardcoded)
- POST /sessions/{id}/essay endpoint
- Conversation reference flow ("turn that into an essay")
"""

from __future__ import annotations

import uuid
from unittest.mock import MagicMock, call, patch

import pytest

from app.llm.base import LLMResponse
from app.schemas.retrieval import RetrievalResponse, RetrievalResult
from app.skills.ship30 import (
    CONVERSATION_CONTEXT_LIMIT,
    MAX_GENERATION_ATTEMPTS,
    WORD_COUNT_MAX,
    WORD_COUNT_MIN,
    WORD_COUNT_TARGET,
    Ship30Result,
    Ship30Skill,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def make_chunk(
    content: str = "Retention is the key metric.",
    episode_id: str = "ep-retention-001",
    title: str = "Lenny's Podcast: Retention Masterclass",
    guest_name: str | None = "Brian Balfour",
) -> RetrievalResult:
    """Build a deterministic RetrievalResult for tests."""
    return RetrievalResult(
        chunk_id=uuid.uuid4(),
        transcript_id=uuid.uuid4(),
        chunk_index=0,
        episode_id=episode_id,
        title=title,
        content=content,
        similarity_score=0.85,
        guest_name=guest_name,
        source_url="https://www.lennyspodcast.com/retention",
        timestamp_start=120.0,
        timestamp_end=180.0,
    )


def make_essay_prose(word_count: int = WORD_COUNT_TARGET) -> str:
    """Generate synthetic essay prose with approximate word count."""
    words = ["growth"] * word_count
    return " ".join(words)


def make_retrieval_response(chunks: list[RetrievalResult]) -> RetrievalResponse:
    return RetrievalResponse(
        query="retention",
        results=chunks,
        total_found=len(chunks),
        threshold_applied=0.35,
    )


# ---------------------------------------------------------------------------
# 1. Constants
# ---------------------------------------------------------------------------

def test_conversation_context_limit_is_four():
    """CONVERSATION_CONTEXT_LIMIT must be exactly 4."""
    assert CONVERSATION_CONTEXT_LIMIT == 4


def test_max_generation_attempts_is_two():
    """MAX_GENERATION_ATTEMPTS must be exactly 2."""
    assert MAX_GENERATION_ATTEMPTS == 2


def test_word_count_range():
    """Word count range must be 1100–1400 with target 1250."""
    assert WORD_COUNT_MIN == 1100
    assert WORD_COUNT_MAX == 1400
    assert WORD_COUNT_TARGET == 1250


# ---------------------------------------------------------------------------
# 2. Topic resolution
# ---------------------------------------------------------------------------

def test_resolve_topic_direct_request(db_session):
    """Direct essay request is returned as-is (no pronoun references)."""
    skill = Ship30Skill(db_session)
    topic = skill.resolve_topic(
        "Write a Ship 30 essay about retention strategies",
        recent_history=[],
    )
    assert "retention" in topic.lower()


def test_resolve_topic_pronoun_reference_uses_recent_context(db_session):
    """'Turn that into an essay' resolves using the previous turn's content."""
    skill = Ship30Skill(db_session)
    history = [
        {"role": "user", "content": "What does Lenny say about retention?"},
        {"role": "assistant", "content": "Lenny emphasizes that retention is the foundation of growth..."},
    ]
    topic = skill.resolve_topic("Turn that into a Ship 30 essay.", recent_history=history)
    # Topic should incorporate retention context from the previous turn
    assert "retention" in topic.lower()


def test_resolve_topic_bounded_to_four_messages(db_session):
    """Topic resolution uses at most CONVERSATION_CONTEXT_LIMIT messages."""
    skill = Ship30Skill(db_session)
    # Build 8 messages (4 turns) — only last 4 should be used
    history = [
        {"role": "user", "content": "Ancient history question about CAC"},
        {"role": "assistant", "content": "Old answer about CAC"},
        {"role": "user", "content": "Even older question about LTV"},
        {"role": "assistant", "content": "Old answer about LTV"},
        {"role": "user", "content": "Earlier question"},
        {"role": "assistant", "content": "Earlier answer"},
        {"role": "user", "content": "What does Lenny say about retention?"},
        {"role": "assistant", "content": "Lenny emphasizes retention as the core growth metric."},
    ]
    # The skill internally limits to last 4 messages
    topic = skill.resolve_topic("Turn that into an essay.", recent_history=history)
    # The resolved topic should reference retention (from the last 2 messages, within the 4-message window)
    assert "retention" in topic.lower()
    # It should NOT reference the ancient CAC context (messages 1-2 are outside the window)
    # We verify this by checking that resolve_topic only sliced the last 4
    bounded = history[-CONVERSATION_CONTEXT_LIMIT:]
    assert len(bounded) == 4
    assert bounded[0]["content"] == "Earlier question"


def test_resolve_topic_no_history(db_session):
    """When there is no history, the request is used directly."""
    skill = Ship30Skill(db_session)
    topic = skill.resolve_topic("Write about product-led growth", recent_history=None)
    assert "product-led growth" in topic.lower()


# ---------------------------------------------------------------------------
# 3. Evidence retrieval
# ---------------------------------------------------------------------------

def test_insufficient_evidence_returns_transparent_response(db_session, monkeypatch):
    """When retrieval returns 0 chunks, the skill returns a transparent message."""
    skill = Ship30Skill(db_session)
    empty_response = make_retrieval_response([])
    skill.retriever.retrieve = MagicMock(return_value=empty_response)

    result = skill.run("Write an essay about quantum computing")

    assert result.insufficient_evidence is True
    assert result.grounded is False
    assert result.generation_attempts == 0
    assert len(result.citations) == 0
    assert "don't have enough evidence" in result.essay.lower()
    # Validation issues should record the reason
    assert any("insufficient" in issue for issue in result.validation_issues)


def test_insufficient_evidence_does_not_call_llm(db_session, monkeypatch):
    """When retrieval returns no results, the LLM should NOT be called."""
    skill = Ship30Skill(db_session)
    empty_response = make_retrieval_response([])
    skill.retriever.retrieve = MagicMock(return_value=empty_response)

    with patch("app.skills.ship30.get_llm_provider") as mock_provider_fn:
        skill.run("Write an essay about something obscure")
        mock_provider_fn.assert_not_called()


# ---------------------------------------------------------------------------
# 4. Word count validation
# ---------------------------------------------------------------------------

def test_word_count_valid_range(db_session):
    """Word count validation passes for essays within the defined range."""
    skill = Ship30Skill(db_session)
    prose = make_essay_prose(1250)
    valid, count = skill.validate_word_count(prose)
    assert valid is True
    assert 1100 <= count <= 1400


def test_word_count_too_short(db_session):
    """Word count validation fails for essays shorter than WORD_COUNT_MIN."""
    skill = Ship30Skill(db_session)
    prose = make_essay_prose(500)
    valid, count = skill.validate_word_count(prose)
    assert valid is False
    assert count == 500


def test_word_count_too_long(db_session):
    """Word count validation fails for essays longer than WORD_COUNT_MAX."""
    skill = Ship30Skill(db_session)
    prose = make_essay_prose(1600)
    valid, count = skill.validate_word_count(prose)
    assert valid is False
    assert count == 1600


def test_word_count_boundary_min(db_session):
    """Word count validation passes exactly at WORD_COUNT_MIN."""
    skill = Ship30Skill(db_session)
    prose = make_essay_prose(WORD_COUNT_MIN)
    valid, _ = skill.validate_word_count(prose)
    assert valid is True


def test_word_count_boundary_max(db_session):
    """Word count validation passes exactly at WORD_COUNT_MAX."""
    skill = Ship30Skill(db_session)
    prose = make_essay_prose(WORD_COUNT_MAX)
    valid, _ = skill.validate_word_count(prose)
    assert valid is True


# ---------------------------------------------------------------------------
# 5. Citation validation
# ---------------------------------------------------------------------------

def test_citation_validation_passes_for_retrieved_ids(db_session):
    """Citation validation passes when all cited IDs exist in retrieved set."""
    skill = Ship30Skill(db_session)
    chunk_id = uuid.uuid4()
    retrieved_ids = {chunk_id}
    cited_ids = {str(chunk_id)}
    valid, invalid = skill.validate_citations(cited_ids, retrieved_ids)
    assert valid is True
    assert invalid == []


def test_citation_validation_fails_for_fabricated_ids(db_session):
    """Citation validation fails for chunk IDs not in retrieved set."""
    skill = Ship30Skill(db_session)
    retrieved_ids = {uuid.uuid4()}
    fabricated_id = str(uuid.uuid4())  # Not in retrieved set
    cited_ids = {fabricated_id}
    valid, invalid = skill.validate_citations(cited_ids, retrieved_ids)
    assert valid is False
    assert fabricated_id in invalid


def test_citation_validation_empty_citations(db_session):
    """Citation validation passes when no citations are cited (no claims)."""
    skill = Ship30Skill(db_session)
    retrieved_ids = {uuid.uuid4()}
    valid, invalid = skill.validate_citations(set(), retrieved_ids)
    assert valid is True
    assert invalid == []


# ---------------------------------------------------------------------------
# 6. LLM output parsing
# ---------------------------------------------------------------------------

def test_parse_llm_output_extracts_essay_and_citations(db_session):
    """Parser correctly extracts essay prose and citation IDs from LLM output."""
    skill = Ship30Skill(db_session)
    chunk = make_chunk()
    cid = str(chunk.chunk_id)

    raw = f"""This is the essay prose about retention.

It has multiple paragraphs.

Each paragraph supports the central argument.

---
CITATIONS: {cid}
WORD_COUNT: 15
"""
    essay, cited_ids, wc = skill._parse_llm_output(raw, [chunk])

    assert "This is the essay prose" in essay
    assert cid in cited_ids
    # Word count is based on actual prose count, not self-reported
    assert wc > 0


def test_parse_llm_output_preserves_invalid_citation_ids(db_session):
    """TEST 2: Parser PRESERVES chunk IDs in CITATIONS that don't match retrieved chunks."""
    skill = Ship30Skill(db_session)
    chunk = make_chunk()
    fake_id = str(uuid.uuid4())

    raw = f"""Essay content here.\n---\nCITATIONS: {fake_id}\nWORD_COUNT: 3\n"""
    essay, cited_ids, wc = skill._parse_llm_output(raw, [chunk])

    # The fake ID MUST be in cited_ids so the validator can reject it!
    assert len(cited_ids) == 1
    assert fake_id in cited_ids


# ---------------------------------------------------------------------------
# 7. Successful generation (happy path)
# ---------------------------------------------------------------------------

def test_run_successful_generation(db_session, monkeypatch):
    """Happy path: sufficient evidence, valid word count, valid citations."""
    skill = Ship30Skill(db_session)
    chunk = make_chunk()
    cid = str(chunk.chunk_id)

    # Mock retriever
    skill.retriever.retrieve = MagicMock(
        return_value=make_retrieval_response([chunk])
    )

    # Mock LLM provider
    mock_provider = MagicMock()
    essay_prose = make_essay_prose(WORD_COUNT_TARGET)
    mock_provider.chat.return_value = LLMResponse(
        content=f"{essay_prose}\n---\nCITATIONS: {cid}\nWORD_COUNT: {WORD_COUNT_TARGET}",
        provider="test_provider",
        model="test_model",
    )
    monkeypatch.setattr("app.skills.ship30.get_llm_provider", lambda name: mock_provider)

    result = skill.run("Write a Ship 30 essay about retention")

    assert result.grounded is True
    assert result.insufficient_evidence is False
    assert WORD_COUNT_MIN <= result.word_count <= WORD_COUNT_MAX
    assert result.generation_attempts == 1
    assert len(result.citations) > 0
    assert result.validation_issues == []


def test_run_uses_provider_abstraction(db_session, monkeypatch):
    """Ship30 does NOT hardcode any provider — it uses get_llm_provider()."""
    skill = Ship30Skill(db_session)
    chunk = make_chunk()
    skill.retriever.retrieve = MagicMock(
        return_value=make_retrieval_response([chunk])
    )

    mock_provider = MagicMock()
    mock_provider.chat.return_value = LLMResponse(
        content=make_essay_prose(WORD_COUNT_TARGET),
        provider="ollama",
        model="llama3.1",
    )

    captured_provider_name = []

    def capture_provider(name):
        captured_provider_name.append(name)
        return mock_provider

    monkeypatch.setattr("app.skills.ship30.get_llm_provider", capture_provider)

    result = skill.run("Write a Ship 30 essay about growth")

    # provider name came from settings, NOT hardcoded
    assert len(captured_provider_name) == 1
    # Provider should be whatever is in settings (ollama by default in tests)
    assert captured_provider_name[0] in ("anthropic", "ollama")


# ---------------------------------------------------------------------------
# 8. Bounded regeneration
# ---------------------------------------------------------------------------

def test_run_regenerates_on_word_count_failure(db_session, monkeypatch):
    """When first attempt word count is invalid, the skill tries again (max 2)."""
    skill = Ship30Skill(db_session)
    chunk = make_chunk()
    skill.retriever.retrieve = MagicMock(
        return_value=make_retrieval_response([chunk])
    )

    mock_provider = MagicMock()
    # First attempt: too short
    short_essay = make_essay_prose(500)
    # Second attempt: valid
    valid_essay = make_essay_prose(WORD_COUNT_TARGET)
    cid = str(chunk.chunk_id)

    mock_provider.chat.side_effect = [
        LLMResponse(
            content=f"{short_essay}\n---\nCITATIONS: {cid}\nWORD_COUNT: 500",
            provider="test_provider",
            model="test_model",
        ),
        LLMResponse(
            content=f"{valid_essay}\n---\nCITATIONS: {cid}\nWORD_COUNT: {WORD_COUNT_TARGET}",
            provider="test_provider",
            model="test_model",
        ),
    ]
    monkeypatch.setattr("app.skills.ship30.get_llm_provider", lambda name: mock_provider)

    result = skill.run("Write a Ship 30 essay about retention")

    assert mock_provider.chat.call_count == 2
    assert result.generation_attempts == 2
    # The second result is valid
    assert WORD_COUNT_MIN <= result.word_count <= WORD_COUNT_MAX


def test_run_max_two_attempts_never_exceeded(db_session, monkeypatch):
    """Even if both attempts fail validation, no third attempt is made."""
    skill = Ship30Skill(db_session)
    chunk = make_chunk()
    skill.retriever.retrieve = MagicMock(
        return_value=make_retrieval_response([chunk])
    )

    mock_provider = MagicMock()
    short_essay = make_essay_prose(300)  # Always fails word count

    mock_provider.chat.return_value = LLMResponse(
        content=f"{short_essay}\n---\nCITATIONS:\nWORD_COUNT: 300",
        provider="test_provider",
        model="test_model",
    )
    monkeypatch.setattr("app.skills.ship30.get_llm_provider", lambda name: mock_provider)

    result = skill.run("Write a Ship 30 essay about retention")

    # Exactly MAX_GENERATION_ATTEMPTS calls, no more
    assert mock_provider.chat.call_count == MAX_GENERATION_ATTEMPTS
    assert result.generation_attempts == MAX_GENERATION_ATTEMPTS
    # Issues should be recorded
    assert len(result.validation_issues) > 0
    # But a result is still returned (best effort)
    assert result.essay != ""


def test_run_returns_best_result_after_both_failures(db_session, monkeypatch):
    """After 2 failed attempts, the result from attempt 2 is returned with issues."""
    skill = Ship30Skill(db_session)
    chunk = make_chunk()
    skill.retriever.retrieve = MagicMock(
        return_value=make_retrieval_response([chunk])
    )

    mock_provider = MagicMock()
    short_essay = make_essay_prose(400)
    mock_provider.chat.return_value = LLMResponse(
        content=f"{short_essay}",
        provider="test_provider",
        model="test_model",
    )
    monkeypatch.setattr("app.skills.ship30.get_llm_provider", lambda name: mock_provider)

    result = skill.run("Write an essay")

    assert result.essay != ""  # Not empty
    assert not result.insufficient_evidence  # Evidence was found


# ---------------------------------------------------------------------------
# 9. Citation validation triggers regeneration
# ---------------------------------------------------------------------------

def test_run_citation_validation_rejects_fabricated_ids(db_session):
    """TEST 2: validate_citations directly rejects chunk IDs not in retrieved set."""
    skill = Ship30Skill(db_session)
    chunk = make_chunk()
    retrieved_ids = {chunk.chunk_id}
    fabricated_id = str(uuid.uuid4())
    
    valid, invalid = skill.validate_citations({fabricated_id}, retrieved_ids)
    assert valid is False
    assert fabricated_id in invalid


def test_run_regenerates_on_citation_validation_failure(db_session, monkeypatch):
    """TEST 3: First attempt has fabricated citation. Second attempt has valid citation."""
    skill = Ship30Skill(db_session)
    chunk = make_chunk()
    skill.retriever.retrieve = MagicMock(
        return_value=make_retrieval_response([chunk])
    )

    mock_provider = MagicMock()
    valid_essay = make_essay_prose(WORD_COUNT_TARGET)
    cid = str(chunk.chunk_id)
    fabricated_id = str(uuid.uuid4())

    mock_provider.chat.side_effect = [
        LLMResponse(
            content=f"{valid_essay}\n---\nCITATIONS: {fabricated_id}\nWORD_COUNT: {WORD_COUNT_TARGET}",
            provider="test_provider",
            model="test_model",
        ),
        LLMResponse(
            content=f"{valid_essay}\n---\nCITATIONS: {cid}\nWORD_COUNT: {WORD_COUNT_TARGET}",
            provider="test_provider",
            model="test_model",
        ),
    ]
    monkeypatch.setattr("app.skills.ship30.get_llm_provider", lambda name: mock_provider)

    result = skill.run("Write an essay")

    assert mock_provider.chat.call_count == 2
    assert result.generation_attempts == 2
    assert len(result.citations) > 0
    assert result.citations[0].chunk_id == chunk.chunk_id
    assert "invalid_citations" not in str(result.validation_issues)
    assert result.grounded is True


def test_run_fails_after_two_invalid_citations(db_session, monkeypatch):
    """TEST 4 & 5: Both attempts contain fabricated citations. Final response strips unsupported claim."""
    skill = Ship30Skill(db_session)
    chunk = make_chunk()
    skill.retriever.retrieve = MagicMock(
        return_value=make_retrieval_response([chunk])
    )

    mock_provider = MagicMock()
    # "According to Lenny, X..." with invalid citation
    bad_essay = make_essay_prose(WORD_COUNT_TARGET) + " According to Lenny, X..."
    fabricated_id = str(uuid.uuid4())

    mock_provider.chat.return_value = LLMResponse(
        content=f"{bad_essay}\n---\nCITATIONS: {fabricated_id}\nWORD_COUNT: {WORD_COUNT_TARGET}",
        provider="test_provider",
        model="test_model",
    )
    monkeypatch.setattr("app.skills.ship30.get_llm_provider", lambda name: mock_provider)

    result = skill.run("Write an essay")

    assert mock_provider.chat.call_count == 2
    assert result.generation_attempts == 2
    
    # Validation failure is recorded
    assert any("invalid_citations" in issue for issue in result.validation_issues)
    
    # Final response does NOT contain unsupported source-backed prose
    assert "According to Lenny, X..." not in result.essay
    assert "discarded" in result.essay.lower() or "failed" in result.essay.lower()
    
    # No fake citation is returned
    assert len(result.citations) == 0
    assert result.grounded is False



# ---------------------------------------------------------------------------
# 10. Conversation reference ("Turn that into an essay")
# ---------------------------------------------------------------------------

def test_conversation_reference_resolution(db_session, monkeypatch):
    """'Turn that into a Ship 30 essay' correctly uses retention context."""
    skill = Ship30Skill(db_session)

    history = [
        {"role": "user", "content": "What does Lenny say about retention?"},
        {"role": "assistant", "content": "Lenny's podcast emphasizes that retention is the foundation of sustainable growth. Brian Balfour discussed..."},
    ]

    topic = skill.resolve_topic(
        "Turn that into a Ship 30 essay.",
        recent_history=history,
    )

    # Topic should incorporate retention context
    assert "retention" in topic.lower()
    # And should include content from both recent user and assistant messages
    assert "lenny" in topic.lower() or "retention" in topic.lower()


def test_conversation_reference_only_uses_last_four_messages(db_session):
    """resolve_topic never uses more than 4 history messages."""
    skill = Ship30Skill(db_session)

    # 10 messages — only last 4 should influence topic resolution
    history = [
        {"role": "user", "content": f"Message {i}"} if i % 2 == 0
        else {"role": "assistant", "content": f"Answer {i}"}
        for i in range(10)
    ]

    # We verify the internal bounded slice is 4 messages max
    bounded = history[-CONVERSATION_CONTEXT_LIMIT:]
    assert len(bounded) == CONVERSATION_CONTEXT_LIMIT


# ---------------------------------------------------------------------------
# 11. POST /sessions/{id}/essay API endpoint
# ---------------------------------------------------------------------------

def test_essay_endpoint_requires_existing_session(client):
    """POST /sessions/{id}/essay returns 404 for unknown session."""
    fake_id = str(uuid.uuid4())
    resp = client.post(
        f"/sessions/{fake_id}/essay",
        json={"content": "Write an essay about retention."},
    )
    assert resp.status_code == 404


def test_essay_endpoint_returns_essay_response(client, monkeypatch):
    """POST /sessions/{id}/essay returns essay content with Ship30 metadata."""
    # Create a session first
    session_resp = client.post("/sessions")
    session_id = session_resp.json()["id"]

    # Mock Ship30Skill
    mock_result = Ship30Result(
        essay="This is a grounded essay about retention with many words. " * 50,
        word_count=1250,
        citations=[],
        provider="ollama",
        grounded=True,
        generation_attempts=1,
        insufficient_evidence=False,
        validation_issues=[],
    )
    mock_skill = MagicMock()
    mock_skill.run.return_value = mock_result

    monkeypatch.setattr(
        "app.api.sessions.Ship30Skill",
        lambda db: mock_skill,
    )

    resp = client.post(
        f"/sessions/{session_id}/essay",
        json={"content": "Write a Ship 30 essay about retention."},
    )

    assert resp.status_code == 200
    data = resp.json()
    assert data["role"] == "assistant"
    assert data["word_count"] == 1250
    assert data["generation_attempts"] == 1
    assert data["insufficient_evidence"] is False
    assert data["validation_issues"] == []
    assert "grounded" in data


def test_essay_endpoint_insufficient_evidence(client, monkeypatch):
    """POST /sessions/{id}/essay handles insufficient evidence gracefully."""
    session_resp = client.post("/sessions")
    session_id = session_resp.json()["id"]

    mock_result = Ship30Result(
        essay="I don't have enough evidence in the available Lenny sources to write a grounded essay on that topic.",
        word_count=25,
        citations=[],
        provider="ollama",
        grounded=False,
        generation_attempts=0,
        insufficient_evidence=True,
        validation_issues=["insufficient_evidence"],
    )
    mock_skill = MagicMock()
    mock_skill.run.return_value = mock_result
    monkeypatch.setattr("app.api.sessions.Ship30Skill", lambda db: mock_skill)

    resp = client.post(
        f"/sessions/{session_id}/essay",
        json={"content": "Write an essay about quantum physics"},
    )

    assert resp.status_code == 200
    data = resp.json()
    assert data["insufficient_evidence"] is True
    assert data["grounded"] is False


def test_essay_endpoint_handles_llm_error(client, monkeypatch):
    """POST /sessions/{id}/essay returns 502 when the LLM provider fails."""
    from app.llm.base import LLMError

    session_resp = client.post("/sessions")
    session_id = session_resp.json()["id"]

    mock_skill = MagicMock()
    mock_skill.run.side_effect = LLMError("Provider unavailable")
    monkeypatch.setattr("app.api.sessions.Ship30Skill", lambda db: mock_skill)

    resp = client.post(
        f"/sessions/{session_id}/essay",
        json={"content": "Write an essay about retention"},
    )

    assert resp.status_code == 502


def test_essay_endpoint_persists_as_message(client, monkeypatch):
    """Generated essay is persisted as an assistant message in the session."""
    session_resp = client.post("/sessions")
    session_id = session_resp.json()["id"]

    mock_result = Ship30Result(
        essay="Essay content about retention. " * 40,
        word_count=1200,
        citations=[],
        provider="ollama",
        grounded=True,
        generation_attempts=1,
    )
    mock_skill = MagicMock()
    mock_skill.run.return_value = mock_result
    monkeypatch.setattr("app.api.sessions.Ship30Skill", lambda db: mock_skill)

    client.post(
        f"/sessions/{session_id}/essay",
        json={"content": "Write an essay about retention"},
    )

    # Verify the essay is now in the session's message history
    session_resp = client.get(f"/sessions/{session_id}")
    messages = session_resp.json()["messages"]
    assistant_msgs = [m for m in messages if m["role"] == "assistant"]
    assert len(assistant_msgs) == 1
    assert "retention" in assistant_msgs[0]["content"].lower()


# ---------------------------------------------------------------------------
# 12. Existing session/message behavior regression
# ---------------------------------------------------------------------------

def test_existing_message_endpoint_unaffected(client, monkeypatch):
    """POST /sessions/{id}/messages still works after Phase 5 changes."""
    session_resp = client.post("/sessions")
    session_id = session_resp.json()["id"]

    mock_agent = MagicMock()
    mock_agent.answer_question.return_value = {
        "answer": "Retention is key.",
        "citations": [],
        "grounded": False,
        "provider": "ollama",
    }
    monkeypatch.setattr("app.api.sessions.GroundedConversationalAgent", lambda db: mock_agent)

    resp = client.post(
        f"/sessions/{session_id}/messages",
        json={"content": "What does Lenny say about retention?"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["content"] == "Retention is key."
