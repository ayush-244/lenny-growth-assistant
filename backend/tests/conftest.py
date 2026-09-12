"""Shared pytest fixtures for Phase 2 integration tests.

Database fixtures
-----------------
The ``db_session`` fixture provides a real SQLAlchemy session against the
Docker PostgreSQL instance. It wraps each test in a transaction that is
rolled back after the test, leaving the database clean for the next test.

Prerequisites
-------------
- docker compose up (PostgreSQL must be running with migrations applied)
- POSTGRES_HOST=localhost in the environment (or .env)

Embedding fixtures
------------------
``deterministic_provider`` returns a DeterministicTestEmbeddingProvider.
Tests must never depend on Ollama availability.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

from app.core.config import settings
from app.rag.embeddings import DeterministicTestEmbeddingProvider


# ---------------------------------------------------------------------------
# Database session fixture
# ---------------------------------------------------------------------------

@pytest.fixture(scope="session")
def db_engine():
    """Create a SQLAlchemy engine connecting to the test database.

    Uses settings.database_url (POSTGRES_HOST from environment).
    Requires Docker PostgreSQL to be running with migrations applied.
    """
    engine = create_engine(settings.database_url, pool_pre_ping=True)
    yield engine
    engine.dispose()


@pytest.fixture()
def db_session(db_engine):
    """Provide a database session wrapped in a rolled-back transaction.

    Each test gets a fresh, isolated session. Changes are never committed
    to the database — the transaction is rolled back after the test.
    """
    connection = db_engine.connect()
    transaction = connection.begin()
    Session = sessionmaker(bind=connection)
    session = Session()

    yield session

    session.close()
    transaction.rollback()
    connection.close()


# ---------------------------------------------------------------------------
# Embedding fixtures
# ---------------------------------------------------------------------------

@pytest.fixture()
def deterministic_provider():
    """Return a DeterministicTestEmbeddingProvider (768-dim, test-only)."""
    return DeterministicTestEmbeddingProvider()


# ---------------------------------------------------------------------------
# Fixture data
# ---------------------------------------------------------------------------

@pytest.fixture()
def sample_fixture():
    """Load the sample episode fixture from the ingestion/fixtures directory."""
    fixture_path = (
        Path(__file__).resolve().parent.parent.parent
        / "ingestion"
        / "fixtures"
        / "sample_episode.json"
    )
    with fixture_path.open("r", encoding="utf-8") as f:
        return json.load(f)
