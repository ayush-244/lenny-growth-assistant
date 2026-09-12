"""Embedding provider abstraction for the Lenny Growth Assistant.

Design
------
EmbeddingProvider is a Protocol — any object with an ``embed(text) -> list[float]``
method is a valid provider. This keeps the retrieval layer decoupled from
the specific embedding backend.

Providers
---------
OllamaEmbeddingProvider
    Calls the local Ollama /api/embeddings endpoint.
    Validates that the returned vector has exactly EMBEDDING_DIMENSION dimensions.
    Raises EmbeddingError with a clear message if Ollama is unavailable or
    returns an unexpected response.

DeterministicTestEmbeddingProvider
    *** TEST-ONLY — never use for real ingestion ***
    Produces repeatable, L2-normalized 768-dim vectors from text.

    Token-overlap-aware design
    ~~~~~~~~~~~~~~~~~~~~~~~~~~
    The text is tokenized by whitespace. Each token is hashed to one of
    EMBEDDING_DIM buckets. The vector component for bucket i is the sum of
    (1 / (1 + token_position)) weights for all tokens that hash to i.
    The result is L2-normalized so cosine similarity is meaningful.

    Consequence: texts that share vocabulary tokens produce vectors with
    correlated components, which means:
      - "growth strategy" and "pricing strategy" share "strategy" → higher
        cosine similarity than "growth strategy" vs "hiring manager"
      - This makes retrieval threshold tests behaviorally meaningful
      - Identical input always produces identical output (deterministic)

    This provider exists so automated tests do not depend on a live Ollama
    installation. It does NOT reflect real semantic meaning and must never
    be used to generate embeddings for production data.
"""

from __future__ import annotations

import hashlib
import logging
import math
from typing import Protocol

import httpx

from app.core.config import settings

logger = logging.getLogger(__name__)


class EmbeddingError(Exception):
    """Raised when an embedding provider fails or returns an invalid response."""


class EmbeddingProvider(Protocol):
    """Protocol for all embedding providers."""

    def embed(self, text: str) -> list[float]:
        """Embed text into a fixed-dimension float vector.

        Parameters
        ----------
        text:
            The input text to embed.

        Returns
        -------
        list[float]
            A vector of exactly EMBEDDING_DIMENSION floats.

        Raises
        ------
        EmbeddingError
            If the provider is unavailable or returns an invalid response.
        """
        ...


class OllamaEmbeddingProvider:
    """Embedding provider backed by a local Ollama instance.

    Calls POST {ollama_base_url}/api/embeddings with the configured model.
    Validates that the returned embedding has exactly `expected_dim` dimensions.

    Raises
    ------
    EmbeddingError
        - If Ollama is unreachable
        - If the API returns an unexpected response structure
        - If the embedding dimension does not match expected_dim
    """

    def __init__(
        self,
        base_url: str | None = None,
        model: str | None = None,
        expected_dim: int | None = None,
        timeout: float = 30.0,
    ) -> None:
        self._base_url = (base_url or settings.ollama_base_url).rstrip("/")
        self._model = model or settings.embedding_model
        self._expected_dim = expected_dim or settings.embedding_dimension
        self._timeout = timeout

    def embed(self, text: str) -> list[float]:
        """Generate an embedding vector for the given text via Ollama."""
        url = f"{self._base_url}/api/embeddings"
        payload = {"model": self._model, "prompt": text}

        logger.debug("Requesting embedding from Ollama model=%r url=%r", self._model, url)

        try:
            response = httpx.post(url, json=payload, timeout=self._timeout)
            response.raise_for_status()
        except httpx.ConnectError as exc:
            raise EmbeddingError(
                f"Cannot connect to Ollama at {self._base_url}. "
                f"Is Ollama running? Start it with: ollama serve\n"
                f"Then pull the model: ollama pull {self._model}\n"
                f"Original error: {exc}"
            ) from exc
        except httpx.HTTPStatusError as exc:
            raise EmbeddingError(
                f"Ollama returned HTTP {exc.response.status_code} for model {self._model!r}. "
                f"Response body: {exc.response.text[:200]}"
            ) from exc
        except httpx.TimeoutException as exc:
            raise EmbeddingError(
                f"Ollama request timed out after {self._timeout}s (model={self._model!r})."
            ) from exc

        data = response.json()
        embedding = data.get("embedding")

        if embedding is None:
            raise EmbeddingError(
                f"Ollama response missing 'embedding' field. Got keys: {list(data.keys())}"
            )
        if not isinstance(embedding, list) or not all(
            isinstance(v, (int, float)) for v in embedding
        ):
            raise EmbeddingError(
                "Ollama 'embedding' field is not a list of numbers."
            )

        actual_dim = len(embedding)
        if actual_dim != self._expected_dim:
            raise EmbeddingError(
                f"Embedding dimension mismatch: expected {self._expected_dim}, "
                f"got {actual_dim} from model {self._model!r}. "
                f"Check EMBEDDING_MODEL and EMBEDDING_DIMENSION in your configuration."
            )

        logger.debug("Received embedding dim=%d from Ollama", actual_dim)
        return [float(v) for v in embedding]


class DeterministicTestEmbeddingProvider:
    """*** TEST-ONLY *** Deterministic embedding provider for automated tests.

    Do NOT use this provider for real ingestion. It produces structured but
    non-semantic vectors that are designed to support meaningful retrieval
    threshold tests, not to reflect real natural language meaning.

    Vector construction
    -------------------
    1. Tokenize text by whitespace (lowercased).
    2. For each token at position p, compute its bucket:
           bucket = int(sha256(token)[:8], 16) % EMBEDDING_DIM
    3. Add weight 1.0 / (1.0 + p) to that bucket component.
    4. L2-normalize the resulting vector.

    Properties
    ----------
    - Exactly EMBEDDING_DIM = 768 dimensions.
    - Deterministic: identical text → identical vector.
    - Texts sharing vocabulary tokens → correlated vector components →
      measurable cosine similarity (supports threshold tests).
    - Different texts → generally different vectors.
    - Normalized: suitable for cosine similarity.
    - Empty string → zero vector (special case: returns uniform small values).
    """

    DIM: int = 768

    def __init__(self, expected_dim: int = 768) -> None:
        if expected_dim != self.DIM:
            raise ValueError(
                f"DeterministicTestEmbeddingProvider only supports dim={self.DIM}, "
                f"got {expected_dim}"
            )
        self._dim = expected_dim

    def embed(self, text: str) -> list[float]:
        """Generate a deterministic test embedding for the given text."""
        tokens = text.lower().split()
        vector = [0.0] * self._dim

        if not tokens:
            # Return a small uniform vector for empty input
            val = 1.0 / math.sqrt(self._dim)
            return [val] * self._dim

        for position, token in enumerate(tokens):
            bucket = self._token_bucket(token)
            weight = 1.0 / (1.0 + position)
            vector[bucket] += weight

        return self._l2_normalize(vector)

    def _token_bucket(self, token: str) -> int:
        """Hash a token to a bucket index in [0, DIM)."""
        digest = hashlib.sha256(token.encode()).hexdigest()
        return int(digest[:8], 16) % self._dim

    def _l2_normalize(self, vector: list[float]) -> list[float]:
        """L2-normalize a vector. Returns uniform vector if norm is zero."""
        norm = math.sqrt(sum(v * v for v in vector))
        if norm == 0.0:
            val = 1.0 / math.sqrt(self._dim)
            return [val] * self._dim
        return [v / norm for v in vector]


def get_embedding_provider() -> EmbeddingProvider:
    """Factory — returns the configured embedding provider.

    Reads ``settings.embedding_provider``. Raises ``EmbeddingError`` for
    unknown providers. Never silently falls back to a different provider.

    Returns
    -------
    EmbeddingProvider
        The configured provider instance.
    """
    provider = settings.embedding_provider.lower()

    if provider == "ollama":
        return OllamaEmbeddingProvider()

    raise EmbeddingError(
        f"Unknown embedding provider: {provider!r}. "
        f"Supported values: 'ollama'. "
        f"Check EMBEDDING_PROVIDER in your configuration."
    )
