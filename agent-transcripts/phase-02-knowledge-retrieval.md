# Phase 2: Knowledge Base, PostgreSQL Schema & Retrieval Foundation

## Objective
Establish the semantic retrieval foundation for The Lenny Growth Assistant.

## Key Technical Decisions
1. **Database:** PostgreSQL 16 with the `pgvector` extension.
2. **Schema:** Managed declaratively using SQLAlchemy, migrated via Alembic.
   - `transcripts` table: Metadata for each podcast episode/newsletter.
   - `chunks` table: Chunked text and vector embeddings.
3. **Embeddings:**
   - Provider: Ollama (`nomic-embed-text`, 768 dimensions).
   - Local deterministic test provider (`hashlib.sha256`-based) for automated tests (no silent fallback in production).
4. **Vector Index:** HNSW (Hierarchical Navigable Small World) with cosine distance (`vector_cosine_ops`), chosen for superior recall over IVFFlat.
5. **Retrieval API:** Uses configurable top K (default 5) and min similarity thresholds.

## Implementation Steps
- Created Pydantic schema for retrieval responses (`RetrievalResponse`, `RetrievalResult`).
- Added SQLAlchemy models (`Transcript`, `Chunk`).
- Set up an Alembic migration (`0001_knowledge_base`) implementing `CREATE EXTENSION IF NOT EXISTS vector` and tables.
- Fixed vector index from `ivfflat` to `hnsw` as requested in architecture review.
- Fixed retrieving SQL to use standard `CAST(:query_vec AS vector)` to prevent SQLAlchemy `text()` syntax confusion.
- Implemented `TranscriptChunker` for length/overlap control (~500 tokens / 50 tokens overlap).
- Implemented `Retriever` executing exact cosine similarity searches against PostgreSQL.
- Implemented `IngestionService` and CLI to chunk, embed, and idempotently save episodes.

## Testing & Verification
- Unit and Integration tests confirm idempotency, sequential chunks, and deterministic similarity rankings (e.g., "pricing strategy" correctly ranking higher against a pricing chunk than a hiring chunk).
- Downgrade strategy explicitly *retains* the `vector` extension but drops Phase 2 tables, preventing cascading destruction of unrelated data.
- Ollama fallback prevention verified (the ingestion script explicitly halts with actionable errors if Ollama is unreachable, rather than faking success).

## Readiness
Phase 2 completed successfully. Ready for Phase 3 (Frontend & Artifact Viewer).
