"""pgvector-backed retrieval for the Lenny Growth Assistant.

Retrieval flow
--------------
1. Embed the query text using the provided EmbeddingProvider.
2. Run a cosine similarity search against the chunks table using pgvector's
   ``<=>`` operator (cosine distance; lower distance = higher similarity).
3. Convert distance to similarity: similarity = 1 - distance.
4. Filter out results below the configured similarity threshold.
5. Return a RetrievalResponse with full citation metadata.

Design decisions
----------------
- Cosine similarity is used (via pgvector's vector_cosine_ops).
- Threshold (RAG_MIN_SIMILARITY) is configurable via settings.
- If no results meet the threshold, an explicit empty RetrievalResponse
  is returned — the retriever never fabricates relevant evidence.
- top_k defaults to settings.rag_top_k but is overridable per call.
"""

from __future__ import annotations

import logging
import time

from sqlalchemy import text
from sqlalchemy.orm import Session

from app.core.config import settings
from app.rag.embeddings import EmbeddingProvider
from app.schemas.retrieval import RetrievalResponse, RetrievalResult

logger = logging.getLogger(__name__)


class Retriever:
    """Retrieves semantically relevant transcript chunks using pgvector.

    Parameters
    ----------
    embedding_provider:
        The provider used to embed query text before similarity search.
    """

    def __init__(self, embedding_provider: EmbeddingProvider) -> None:
        self._embedding_provider = embedding_provider

    def retrieve(
        self,
        query: str,
        db: Session,
        top_k: int | None = None,
        min_similarity: float | None = None,
    ) -> RetrievalResponse:
        """Retrieve the most relevant chunks for a query.

        Parameters
        ----------
        query:
            The natural-language query text.
        db:
            An active SQLAlchemy Session.
        top_k:
            Maximum number of results to return (default: settings.rag_top_k).
        min_similarity:
            Minimum cosine similarity threshold (default: settings.rag_min_similarity).
            Results below this threshold are excluded from the response.

        Returns
        -------
        RetrievalResponse
            Contains ordered results with citation metadata. Returns an explicit
            empty response (has_results == False) if no chunks meet the threshold.
        """
        k = top_k if top_k is not None else settings.rag_top_k
        threshold = (
            min_similarity if min_similarity is not None else settings.rag_min_similarity
        )

        t0 = time.perf_counter()

        # 1. Embed the query
        query_embedding = self._embedding_provider.embed(query)

        # 2. pgvector cosine distance query with JOIN to get citation metadata
        #    <=> is cosine distance (0 = identical, 2 = opposite)
        #    similarity = 1 - distance
        sql = text(
            """
            SELECT
                c.id            AS chunk_id,
                c.transcript_id AS transcript_id,
                c.content       AS content,
                c.chunk_index   AS chunk_index,
                c.timestamp_start AS timestamp_start,
                c.timestamp_end   AS timestamp_end,
                1 - (c.embedding <=> CAST(:query_vec AS vector)) AS similarity_score,
                t.episode_id    AS episode_id,
                t.title         AS title,
                t.guest_name    AS guest_name,
                t.source_url    AS source_url
            FROM chunks c
            JOIN transcripts t ON t.id = c.transcript_id
            ORDER BY c.embedding <=> CAST(:query_vec AS vector)
            LIMIT :top_k
            """
        )

        embedding_str = "[" + ",".join(str(v) for v in query_embedding) + "]"
        rows = db.execute(
            sql,
            {"query_vec": embedding_str, "top_k": k},
        ).fetchall()

        # 3. Filter by threshold and build response objects
        results: list[RetrievalResult] = []
        for row in rows:
            score = float(row.similarity_score)
            if score < threshold:
                continue
            results.append(
                RetrievalResult(
                    chunk_id=row.chunk_id,
                    transcript_id=row.transcript_id,
                    content=row.content,
                    similarity_score=score,
                    episode_id=row.episode_id,
                    title=row.title,
                    guest_name=row.guest_name,
                    source_url=row.source_url,
                    timestamp_start=row.timestamp_start,
                    timestamp_end=row.timestamp_end,
                    chunk_index=row.chunk_index,
                )
            )

        elapsed_ms = (time.perf_counter() - t0) * 1000
        logger.info(
            "Retrieval complete query=%r top_k=%d threshold=%.2f "
            "candidates=%d returned=%d latency_ms=%.1f",
            query[:80],
            k,
            threshold,
            len(rows),
            len(results),
            elapsed_ms,
        )

        return RetrievalResponse(
            query=query,
            results=results,
            total_found=len(results),
            threshold_applied=threshold,
        )
