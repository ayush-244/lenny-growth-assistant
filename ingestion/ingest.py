#!/usr/bin/env python3
"""Ingestion CLI for the Lenny Growth Assistant.

Usage (from repository root):

    python ingestion/ingest.py --file ingestion/fixtures/sample_episode.json

This script runs from the repository root. It adds the backend/ directory to
sys.path automatically so application imports work without any additional
environment variable configuration.

Requirements:
  - docker compose up  (PostgreSQL must be running)
  - Ollama must be running with the embedding model pulled:
        ollama serve
        ollama pull nomic-embed-text
  - Environment: copy .env.example to .env and configure as needed.

Notes:
  - Only OllamaEmbeddingProvider is used for real ingestion.
  - This script will NEVER silently fall back to a fake/test embedding provider.
  - If Ollama is unavailable, the script exits immediately with a clear error.
  - Ingestion is idempotent: running twice on the same episode_id replaces
    the existing chunks rather than creating duplicates.
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
from pathlib import Path

# ---------------------------------------------------------------------------
# Path setup — must happen before any app imports so that `from app.xxx import`
# works when executing `python ingestion/ingest.py` from the repository root.
# ---------------------------------------------------------------------------
_REPO_ROOT = Path(__file__).resolve().parent.parent
_BACKEND_DIR = _REPO_ROOT / "backend"
if str(_BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(_BACKEND_DIR))

# ---------------------------------------------------------------------------
# Application imports — after path setup
# ---------------------------------------------------------------------------
from app.db.database import SessionLocal  # noqa: E402
from app.rag.embeddings import EmbeddingError, OllamaEmbeddingProvider  # noqa: E402
from app.services.ingestion import IngestionService  # noqa: E402

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("ingest")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Ingest a transcript fixture into the Lenny Growth Assistant knowledge base.",
        epilog=(
            "Example:\n"
            "  python ingestion/ingest.py --file ingestion/fixtures/sample_episode.json"
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--file",
        required=True,
        metavar="PATH",
        help="Path to a JSON transcript fixture file.",
    )
    return parser.parse_args()


def load_fixture(path: str) -> dict:
    fixture_path = Path(path)
    if not fixture_path.exists():
        logger.error("Fixture file not found: %s", fixture_path)
        sys.exit(1)
    try:
        with fixture_path.open("r", encoding="utf-8") as f:
            return json.load(f)
    except json.JSONDecodeError as exc:
        logger.error("Invalid JSON in fixture file %s: %s", fixture_path, exc)
        sys.exit(1)


def main() -> None:
    args = parse_args()
    fixture = load_fixture(args.file)

    episode_id = fixture.get("episode_id", "<unknown>")
    logger.info("Starting ingestion for episode_id=%r", episode_id)

    # Only real embeddings — no silent fallback to test provider
    try:
        embedding_provider = OllamaEmbeddingProvider()
        # Probe connectivity with a short test embedding
        logger.info(
            "Probing Ollama at %s with model %s ...",
            embedding_provider._base_url,
            embedding_provider._model,
        )
        embedding_provider.embed("connectivity test")
        logger.info("Ollama embedding provider is available.")
    except EmbeddingError as exc:
        logger.error(
            "Ollama embedding provider is unavailable.\n\n"
            "To fix this:\n"
            "  1. Start Ollama:            ollama serve\n"
            "  2. Pull the model:          ollama pull %s\n"
            "  3. Retry this command.\n\n"
            "Error details: %s",
            embedding_provider._model,
            exc,
        )
        sys.exit(1)

    service = IngestionService()
    db = SessionLocal()
    try:
        result = service.ingest_episode(fixture, db, embedding_provider)
        db.commit()
        logger.info(
            "Ingestion successful:\n"
            "  episode_id    : %s\n"
            "  transcript_id : %s\n"
            "  chunks_created: %d\n"
            "  was_update    : %s",
            result.episode_id,
            result.transcript_id,
            result.chunks_created,
            result.was_update,
        )
    except Exception as exc:
        db.rollback()
        logger.error("Ingestion failed — database rolled back. Error: %s", exc)
        sys.exit(1)
    finally:
        db.close()


if __name__ == "__main__":
    main()
