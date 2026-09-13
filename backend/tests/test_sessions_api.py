"""Tests for the Sessions API."""

from unittest.mock import MagicMock
import uuid

import pytest
from app.core.config import settings


def test_create_session(client):
    """Test POST /sessions."""
    response = client.post("/sessions")
    assert response.status_code == 201
    data = response.json()
    assert "id" in data
    assert data["model_provider"] == "ollama"


def test_get_session(client, db_session):
    """Test GET /sessions/{id}."""
    create_resp = client.post("/sessions")
    session_id = create_resp.json()["id"]
    
    get_resp = client.get(f"/sessions/{session_id}")
    assert get_resp.status_code == 200
    data = get_resp.json()
    assert data["id"] == session_id
    assert "messages" in data
    assert len(data["messages"]) == 0


def test_update_session_provider_persists_per_session(client):
    first = client.post("/sessions").json()["id"]
    second = client.post("/sessions").json()["id"]

    updated = client.patch(f"/sessions/{first}/provider", json={"provider": "anthropic"})
    assert updated.status_code == 200
    assert updated.json()["provider"] == "anthropic"
    assert updated.json()["model"]

    assert client.get(f"/sessions/{first}").json()["model_provider"] == "anthropic"
    assert client.get(f"/sessions/{second}").json()["model_provider"] == "ollama"


def test_update_session_provider_accepts_ollama(client):
    session_id = client.post("/sessions").json()["id"]
    response = client.patch(f"/sessions/{session_id}/provider", json={"provider": "ollama"})
    assert response.status_code == 200
    assert response.json()["provider"] == "ollama"
    assert client.get(f"/sessions/{session_id}").json()["model_provider"] == "ollama"


def test_update_session_provider_rejects_unknown_provider(client):
    session_id = client.post("/sessions").json()["id"]
    assert client.patch(f"/sessions/{session_id}/provider", json={"provider": "unknown"}).status_code == 422


def test_update_session_provider_returns_404_for_missing_session(client):
    missing_id = uuid.uuid4()
    assert client.patch(f"/sessions/{missing_id}/provider", json={"provider": "ollama"}).status_code == 404


def test_create_message(client, monkeypatch):
    """Test POST /sessions/{id}/messages."""
    # Create session
    create_resp = client.post("/sessions")
    session_id = create_resp.json()["id"]
    
    # Mock the Agent
    mock_agent = MagicMock()
    mock_agent.answer_question.return_value = {
        "answer": "Mock answer",
        "citations": [],
        "grounded": False,
        "provider": "ollama"
    }
    
    # We patch GroundedConversationalAgent so it doesn't try to use real LLM
    monkeypatch.setattr(
        "app.api.sessions.GroundedConversationalAgent",
        lambda db: mock_agent
    )
    
    # Send message
    msg_resp = client.post(
        f"/sessions/{session_id}/messages",
        json={"content": "Hello"}
    )
    
    assert msg_resp.status_code == 200
    data = msg_resp.json()
    assert data["role"] == "assistant"
    assert data["content"] == "Mock answer"
    assert data["session_id"] == session_id
    mock_agent.answer_question.assert_called_once()
    assert mock_agent.answer_question.call_args.kwargs["provider_name"] == "ollama"


def test_chat_uses_session_provider_without_mutating_global_settings(client, monkeypatch):
    monkeypatch.setattr(settings, "model_provider", "anthropic")
    session_id = client.post("/sessions").json()["id"]
    client.patch(f"/sessions/{session_id}/provider", json={"provider": "ollama"})
    mock_agent = MagicMock()
    mock_agent.answer_question.return_value = {
        "answer": "Mock answer", "citations": [], "grounded": False, "provider": "ollama"
    }
    monkeypatch.setattr("app.api.sessions.GroundedConversationalAgent", lambda db: mock_agent)

    response = client.post(f"/sessions/{session_id}/messages", json={"content": "Hello"})
    assert response.status_code == 200
    assert response.json()["provider"] == "ollama"
    assert mock_agent.answer_question.call_args.kwargs["provider_name"] == "ollama"
    assert settings.model_provider == "anthropic"
