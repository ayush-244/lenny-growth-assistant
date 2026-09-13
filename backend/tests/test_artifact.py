"""Tests for Artifact generation and management."""

import uuid
from unittest.mock import MagicMock

import pytest

from app.llm.base import LLMResponse, LLMError
from app.schemas.retrieval import RetrievalResponse, RetrievalResult
from app.skills.artifact import ArtifactSkill
from app.services.artifact import ArtifactService


def make_chunk() -> RetrievalResult:
    return RetrievalResult(
        chunk_id=uuid.uuid4(),
        transcript_id=uuid.uuid4(),
        chunk_index=0,
        episode_id="ep-001",
        title="Test Title",
        content="Test content.",
        similarity_score=0.85,
    )


def test_artifact_skill_invalid_type(db_session):
    skill = ArtifactSkill(db_session)
    result = skill.run("Create something", "pdf", [])
    
    assert result.grounded is False
    assert "Invalid artifact type" in result.content
    assert "invalid_artifact_type" in result.validation_issues


def test_artifact_skill_insufficient_evidence(db_session, monkeypatch):
    skill = ArtifactSkill(db_session)
    skill.retriever.retrieve = MagicMock(
        return_value=RetrievalResponse(query="test", results=[], total_found=0, threshold_applied=0.35)
    )
    
    result = skill.run("Write an artifact about X", "markdown", [])
    
    assert result.grounded is False
    assert result.insufficient_evidence is True
    assert "insufficient_evidence" in result.validation_issues


def test_artifact_skill_html_strips_markdown_wrappers(db_session, monkeypatch):
    skill = ArtifactSkill(db_session)
    chunk = make_chunk()
    skill.retriever.retrieve = MagicMock(
        return_value=RetrievalResponse(query="test", results=[chunk], total_found=1, threshold_applied=0.35)
    )
    
    mock_provider = MagicMock()
    mock_provider.chat.return_value = LLMResponse(
        content="```html\n<div>Test</div>\n```",
        provider="test",
        model="test",
    )
    monkeypatch.setattr("app.skills.artifact.get_llm_provider", lambda name: mock_provider)
    
    result = skill.run("Make HTML", "html", [])
    
    # Should strip ```html and ``` and inject CSP
    assert "```html" not in result.content
    assert "Content-Security-Policy" in result.content
    assert "<div>Test</div>" in result.content
    assert result.grounded is True


def test_artifact_service_isolation(db_session):
    session1_id = uuid.uuid4()
    session2_id = uuid.uuid4()
    
    # Needs valid sessions first
    from app.models.session import Session
    s1 = Session(id=session1_id, model_provider="test")
    s2 = Session(id=session2_id, model_provider="test")
    db_session.add_all([s1, s2])
    db_session.commit()
    
    svc = ArtifactService(db_session)
    a1 = svc.create_artifact(session1_id, "markdown", "c1", "r1")
    a2 = svc.create_artifact(session2_id, "html", "c2", "r2")
    
    # Session 1 lists only a1
    l1 = svc.list_artifacts(session1_id)
    assert len(l1) == 1
    assert l1[0].id == a1.id
    
    # Session 1 cannot get a2
    fetch = svc.get_artifact(session1_id, a2.id)
    assert fetch is None


def test_api_create_artifact(client, monkeypatch):
    session_resp = client.post("/sessions")
    session_id = session_resp.json()["id"]
    
    mock_skill = MagicMock()
    from app.skills.artifact import ArtifactSkillResult
    mock_skill.run.return_value = ArtifactSkillResult(
        content="# Markdown",
        artifact_type="markdown",
        provider="test",
        grounded=True,
    )
    monkeypatch.setattr("app.api.sessions.ArtifactSkill", lambda db: mock_skill)
    
    resp = client.post(
        f"/sessions/{session_id}/artifacts",
        json={"request": "Do something", "artifact_type": "markdown"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["content"] == "# Markdown"
    assert data["artifact_type"] == "markdown"
    assert data["grounded"] is True
    assert mock_skill.run.call_args.kwargs["provider_name"] == "ollama"


def test_api_create_artifact_llm_error(client, monkeypatch):
    session_resp = client.post("/sessions")
    session_id = session_resp.json()["id"]
    
    mock_skill = MagicMock()
    mock_skill.run.side_effect = LLMError("Test error")
    monkeypatch.setattr("app.api.sessions.ArtifactSkill", lambda db: mock_skill)
    
    resp = client.post(
        f"/sessions/{session_id}/artifacts",
        json={"request": "Do something", "artifact_type": "markdown"},
    )
    assert resp.status_code == 502
