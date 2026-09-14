"""Shared pytest fixtures for integration tests.

Database fixtures
-----------------
The ``db_session`` fixture provides a real SQLAlchemy session against the
Docker PostgreSQL instance. Each test runs inside a transaction that is
rolled back after the test.

The transcript and chunk tables are cleared inside that transaction before
each test so tests remain isolated from manually ingested demo data.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, delete
from sqlalchemy.orm import sessionmaker

from app.core.config import settings
from app.db.database import get_db
from app.models.chunk import Chunk
from app.models.transcript import Transcript
from app.rag.embeddings import DeterministicTestEmbeddingProvider
from app.main import app


# ---------------------------------------------------------------------------
# Database session fixture
# ---------------------------------------------------------------------------

@pytest.fixture(scope="session")
def db_engine():
    """Create a SQLAlchemy engine connecting to PostgreSQL."""

    engine = create_engine(
        settings.database_url,
        pool_pre_ping=True,
    )

    yield engine

    engine.dispose()


@pytest.fixture()
def db_session(db_engine):
    """Provide an isolated database session for each test."""

    connection = db_engine.connect()
    transaction = connection.begin()

    Session = sessionmaker(bind=connection)
    session = Session()

    # Remove manually ingested demo data inside the test transaction.
    # The transaction is rolled back after the test, so the real database
    # contents are preserved.
    session.execute(delete(Chunk))
    session.execute(delete(Transcript))

    session.flush()

    yield session

    session.close()
    transaction.rollback()
    connection.close()


# ---------------------------------------------------------------------------
# Embedding fixtures
# ---------------------------------------------------------------------------

@pytest.fixture()
def deterministic_provider():
    """Return a deterministic 768-dimensional test embedding provider."""

    return DeterministicTestEmbeddingProvider()


# ---------------------------------------------------------------------------
# Fixture data
# ---------------------------------------------------------------------------

@pytest.fixture()
def sample_fixture():
    """Load the sample episode fixture."""

    fixture_path = (
        Path(__file__).resolve().parent
        / "fixtures"
        / "sample_episode.json"
    )

    with fixture_path.open(
        "r",
        encoding="utf-8",
    ) as f:
        return json.load(f)


# ---------------------------------------------------------------------------
# API Client fixture
# ---------------------------------------------------------------------------

@pytest.fixture()
def client(db_session):
    """Return a FastAPI TestClient using the isolated DB session."""

    def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db

    with TestClient(app) as test_client:
        yield test_client

    app.dependency_overrides.clear()