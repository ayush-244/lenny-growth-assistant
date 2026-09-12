"""Tests for the Sessions API."""

from unittest.mock import MagicMock
import uuid

import pytest


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
