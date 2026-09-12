"""Tests for the embedding providers.

These are pure unit tests — no database or network required.
"""

import math

import pytest

from app.rag.embeddings import (
    DeterministicTestEmbeddingProvider,
    EmbeddingError,
    OllamaEmbeddingProvider,
)

EXPECTED_DIM = 768


# ---------------------------------------------------------------------------
# DeterministicTestEmbeddingProvider
# ---------------------------------------------------------------------------

class TestDeterministicProvider:
    def setup_method(self):
        self.provider = DeterministicTestEmbeddingProvider()

    def test_returns_correct_dimension(self):
        result = self.provider.embed("hello world")
        assert len(result) == EXPECTED_DIM

    def test_identical_input_produces_identical_vector(self):
        text = "growth strategy pricing"
        v1 = self.provider.embed(text)
        v2 = self.provider.embed(text)
        assert v1 == v2

    def test_different_text_produces_different_vector(self):
        v1 = self.provider.embed("pricing strategy for SaaS products")
        v2 = self.provider.embed("hiring manager interview process onboarding")
        assert v1 != v2

    def test_vector_is_l2_normalized(self):
        """The L2 norm of the output vector should be ~1.0."""
        v = self.provider.embed("some sample text for normalization test")
        norm = math.sqrt(sum(x * x for x in v))
        assert abs(norm - 1.0) < 1e-6, f"Expected L2 norm ~1.0, got {norm}"

    def test_empty_text_returns_correct_dimension(self):
        result = self.provider.embed("")
        assert len(result) == EXPECTED_DIM

    def test_empty_text_is_normalized(self):
        v = self.provider.embed("")
        norm = math.sqrt(sum(x * x for x in v))
        assert abs(norm - 1.0) < 1e-6

    def test_all_elements_are_floats(self):
        v = self.provider.embed("test")
        assert all(isinstance(x, float) for x in v)

    def test_pricing_texts_more_similar_than_unrelated(self):
        """Texts sharing vocabulary should produce higher cosine similarity.

        This validates the token-overlap-aware design: 'pricing strategy'
        and 'our pricing model' share the token 'pricing', so they should
        have higher cosine similarity than 'pricing strategy' and
        'hiring manager'.
        """
        def cosine_sim(a: list[float], b: list[float]) -> float:
            dot = sum(x * y for x, y in zip(a, b))
            # Vectors are already L2-normalized, so dot product == cosine similarity
            return dot

        v_query = self.provider.embed("pricing strategy")
        v_related = self.provider.embed("our pricing model and revenue")
        v_unrelated = self.provider.embed("hiring manager interview onboarding")

        sim_related = cosine_sim(v_query, v_related)
        sim_unrelated = cosine_sim(v_query, v_unrelated)

        assert sim_related > sim_unrelated, (
            f"Expected pricing texts to be more similar than unrelated texts. "
            f"sim_related={sim_related:.4f}, sim_unrelated={sim_unrelated:.4f}"
        )

    def test_wrong_dimension_raises(self):
        with pytest.raises(ValueError, match="only supports dim=768"):
            DeterministicTestEmbeddingProvider(expected_dim=512)


# ---------------------------------------------------------------------------
# Dimension validation (shared logic tested via DeterministicProvider)
# ---------------------------------------------------------------------------

class TestDimensionValidation:
    def test_correct_dimension_accepted(self):
        provider = DeterministicTestEmbeddingProvider(expected_dim=768)
        result = provider.embed("test text")
        assert len(result) == 768

    def test_dimension_validation_on_wrong_dim(self):
        """If a provider returned a wrong-dimension vector, EmbeddingError should be raised.

        We simulate this by monkey-patching the Ollama provider's _expected_dim.
        """
        provider = OllamaEmbeddingProvider.__new__(OllamaEmbeddingProvider)
        provider._expected_dim = 512
        provider._base_url = "http://localhost:11434"
        provider._model = "nomic-embed-text"
        provider._timeout = 5.0

        # Build a fake response that returns 768 dims (wrong for our patched expected_dim=512)
        import unittest.mock as mock
        fake_response = mock.MagicMock()
        fake_response.json.return_value = {"embedding": [0.1] * 768}
        fake_response.raise_for_status = mock.MagicMock()

        with mock.patch("httpx.post", return_value=fake_response):
            with pytest.raises(EmbeddingError, match="dimension mismatch"):
                provider.embed("test")

    def test_missing_embedding_field_raises(self):
        import unittest.mock as mock
        provider = OllamaEmbeddingProvider.__new__(OllamaEmbeddingProvider)
        provider._expected_dim = 768
        provider._base_url = "http://localhost:11434"
        provider._model = "nomic-embed-text"
        provider._timeout = 5.0

        fake_response = mock.MagicMock()
        fake_response.json.return_value = {"no_embedding_key": True}
        fake_response.raise_for_status = mock.MagicMock()

        with mock.patch("httpx.post", return_value=fake_response):
            with pytest.raises(EmbeddingError, match="missing 'embedding' field"):
                provider.embed("test")

    def test_connect_error_raises_embedding_error(self):
        import httpx
        import unittest.mock as mock
        provider = OllamaEmbeddingProvider.__new__(OllamaEmbeddingProvider)
        provider._expected_dim = 768
        provider._base_url = "http://localhost:11434"
        provider._model = "nomic-embed-text"
        provider._timeout = 5.0

        with mock.patch("httpx.post", side_effect=httpx.ConnectError("refused")):
            with pytest.raises(EmbeddingError, match="Cannot connect to Ollama"):
                provider.embed("test")
