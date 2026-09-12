"""LLM provider base types.

LLMProvider
    Protocol — any object with a ``chat()`` method is a valid provider.
    This decouples the agent/orchestrator from specific LLM backends.

LLMResponse
    Structured response returned by every provider.
    Contains the answer text plus any tool-call metadata used
    to derive citation information.

LLMError
    Raised for all LLM provider failures: connection errors, auth errors,
    timeout errors, and unsupported provider names.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Protocol


class LLMError(Exception):
    """Raised when an LLM provider fails or is misconfigured."""


@dataclass
class LLMResponse:
    """Structured response from an LLM provider.

    Attributes
    ----------
    content:
        The final answer text from the model.
    provider:
        The provider name that generated this response (e.g. 'ollama', 'anthropic').
    model:
        The model identifier used (e.g. 'llama3.1:8b', 'claude-haiku-4-5').
    tool_calls_made:
        Number of tool calls the model made during this response (0 for Ollama
        when no tool-calling occurred).
    raw_metadata:
        Optional dict with provider-specific metadata (usage stats, stop_reason, etc.).
        Never contains API keys or secrets.
    """

    content: str
    provider: str
    model: str
    tool_calls_made: int = 0
    raw_metadata: dict[str, Any] = field(default_factory=dict)


class LLMProvider(Protocol):
    """Protocol for all LLM providers.

    Any object implementing this interface can be used by the agent orchestrator.
    Providers are responsible for:
    - Executing tool-use loops internally (Anthropic agentic pattern).
    - Returning a clean LLMResponse with the final answer.
    - Raising LLMError on all failure conditions.
    - Never falling back silently to a different provider.
    """

    def chat(
        self,
        messages: list[dict[str, str]],
        system_prompt: str | None = None,
        tools: list[dict] | None = None,
        tool_executor: Any | None = None,
    ) -> LLMResponse:
        """Send a conversation to the LLM and return the response.

        Parameters
        ----------
        messages:
            List of message dicts with 'role' ('user'/'assistant') and 'content' keys.
        system_prompt:
            Optional system-level instruction prepended to the conversation.
        tools:
            Optional list of tool definitions in the provider's native format.
        tool_executor:
            Callable that executes a named tool: ``tool_executor(name, input) -> str``.
            Required when tools is non-empty.

        Returns
        -------
        LLMResponse
            The final response after all tool-use rounds complete.

        Raises
        ------
        LLMError
            If the provider is unavailable, credentials are invalid,
            or a timeout occurs.
        """
        ...
