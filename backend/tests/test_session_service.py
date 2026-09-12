"""Tests for the SessionService."""

import pytest

from app.services.session import SessionService, SessionNotFoundError


def test_create_session(db_session):
    """Test session creation."""
    svc = SessionService(db_session)
    sess = svc.create_session(metadata={"source": "test"})
    assert sess.id is not None
    assert sess.model_provider == "ollama"  # Default in settings
    assert sess.metadata_ == {"source": "test"}


def test_add_messages_and_get_history(db_session):
    """Test message addition and bounded history retrieval."""
    svc = SessionService(db_session)
    sess = svc.create_session()
    
    import time
    msg1 = svc.add_user_message(sess.id, "Hi")
    time.sleep(0.01) # Small delay to ensure timestamp difference in SQLite/some test dbs
    msg2 = svc.add_assistant_message(
        sess.id,
        content="Hello!",
        citations=[{"title": "Test Episode"}],
        grounded=True,
        provider="ollama"
    )
    
    # Alternatively explicitly alter them if we have to, but SQLAlchemy with actual Postgres timestamps should be fixed if we just sort by created_at.asc() internally for the query.
    # Wait, the problem is SessionService orders by created_at.desc(), but if they have the EXACT same timestamp (because they are in the same transaction and Postgres now() is transaction-bound), they come out arbitrarily.
    # We can fix this by setting the time manually:
    from datetime import datetime, timedelta, timezone
    now = datetime.now(timezone.utc)
    msg1.created_at = now - timedelta(seconds=1)
    msg2.created_at = now
    db_session.commit()
    
    history = svc.get_recent_history(sess.id)
    assert len(history) == 2
    assert history[0]["role"] == "user"
    assert history[0]["content"] == "Hi"
    assert history[1]["role"] == "assistant"
    assert history[1]["content"] == "Hello!"


def test_get_session_not_found(db_session):
    """Test invalid session ID."""
    svc = SessionService(db_session)
    import uuid
    with pytest.raises(SessionNotFoundError):
        svc.get_session(uuid.uuid4())
