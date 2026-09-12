"""LLM provider router.

Selects the correct provider based on MODEL_PROVIDER configuration.

Supported values:
    anthropic → AnthropicProvider
    ollama    → OllamaProvider

Any other value raises LLMError immediately — there is no silent fallback.
This is intentional: provider selection must be deliberate and explicit.
"""

from __future__ import annotations

import logging

from app.core.config import settings
from app.llm.base import LLMError, LLMProvider

logger = logging.getLogger(__name__)

_SUPPORTED_PROVIDERS = ("anthropic", "ollama")


class LLMRouter:
    """Selects an LLM provider from configuration.

    Usage
    -----
    provider = LLMRouter().get_provider()
    response = provider.chat(messages, system_prompt=...)
    """

    def get_provider(
        self,
        provider_name: str | None = None,
    ) -> LLMProvider:
        """Return the configured LLM provider.

        Parameters
        ----------
        provider_name:
            Override the provider name. Defaults to settings.model_provider.

        Returns
        -------
        LLMProvider
            The instantiated provider.

        Raises
        ------
        LLMError
            If provider_name is not a supported value, or if provider
            instantiation fails (e.g. missing API key).
        """
        name = (provider_name or settings.model_provider).lower().strip()

        if name not in _SUPPORTED_PROVIDERS:
            raise LLMError(
                f"Unknown MODEL_PROVIDER: {name!r}. "
                f"Supported values: {', '.join(_SUPPORTED_PROVIDERS)}. "
                f"There is no automatic fallback — update MODEL_PROVIDER in your .env file."
            )

        logger.info("LLMRouter: selecting provider=%r", name)

        if name == "anthropic":
            from app.llm.anthropic import AnthropicProvider
            return AnthropicProvider()

        if name == "ollama":
            from app.llm.ollama import OllamaProvider
            return OllamaProvider()

        # Unreachable given the check above, but satisfies type checkers
        raise LLMError(f"Provider {name!r} is listed as supported but has no implementation.")


def get_llm_provider(provider_name: str | None = None) -> LLMProvider:
    """Convenience function: returns the configured LLM provider.

    Equivalent to ``LLMRouter().get_provider(provider_name)``.
    """
    return LLMRouter().get_provider(provider_name)
