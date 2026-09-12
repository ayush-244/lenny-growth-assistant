"""LLM provider abstraction layer.

Exports:
    LLMProvider  — Protocol defining the provider interface.
    LLMResponse  — Dataclass returned by every provider.
    LLMError     — Raised when a provider fails or is misconfigured.
"""

from app.llm.base import LLMError, LLMProvider, LLMResponse
from app.llm.router import LLMRouter, get_llm_provider

__all__ = [
    "LLMProvider",
    "LLMResponse",
    "LLMError",
    "LLMRouter",
    "get_llm_provider",
]
