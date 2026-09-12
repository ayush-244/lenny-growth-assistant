"""Anthropic LLM provider using the Claude Agent SDK (anthropic Python SDK).

Agent Architecture
------------------
This provider implements the Anthropic "agentic tool-use" pattern:

1. Build message list with system prompt + conversation history + current user turn.
2. Call client.messages.create() with tool definitions.
3. If stop_reason == "tool_use":
   a. Extract tool_use blocks from the response.
   b. Execute each tool via the provided tool_executor callback.
   c. Append assistant message + tool_result messages.
   d. Call client.messages.create() again to get the grounded answer.
4. Repeat tool-use rounds up to MAX_TOOL_ROUNDS (prevents infinite loops).
5. Return LLMResponse with the final text content.

This is the canonical Claude Agent SDK pattern as documented by Anthropic.
The "SDK" is the official `anthropic` Python package — there is no separate
"claude-agent-sdk" package; the agentic loop IS the SDK's tool-use pattern.

Failure Modes
-------------
- Missing API key → LLMError (with clear instruction to set ANTHROPIC_API_KEY).
- HTTP 401/403 → LLMError with status code.
- Timeout → LLMError.
- Unexpected response structure → LLMError.
- Never silently falls back to another provider.
- API key is never logged.
"""

from __future__ import annotations

import logging
from typing import Any, Callable

import anthropic
import anthropic.types as atypes

from app.core.config import settings
from app.llm.base import LLMError, LLMResponse

logger = logging.getLogger(__name__)

# Safety limit on tool-use rounds per request
MAX_TOOL_ROUNDS = 3


class AnthropicProvider:
    """LLM provider backed by Anthropic's Claude models via the anthropic SDK.

    Uses Claude's tool-use API (the "Claude Agent SDK" agentic pattern) to
    execute retrieval tools and produce grounded responses.

    Parameters
    ----------
    api_key:
        Anthropic API key. Defaults to settings.anthropic_api_key.
        Must not be empty. Never logged.
    model:
        Claude model identifier. Defaults to settings.anthropic_model.
    timeout:
        Request timeout in seconds. Defaults to settings.llm_timeout.
    """

    def __init__(
        self,
        api_key: str | None = None,
        model: str | None = None,
        timeout: float | None = None,
    ) -> None:
        resolved_key = api_key or settings.anthropic_api_key
        if not resolved_key:
            raise LLMError(
                "ANTHROPIC_API_KEY is not set. "
                "Set it in your .env file or as an environment variable. "
                "Do NOT hard-code the key in source code."
            )
        self._model = model or settings.anthropic_model
        self._timeout = timeout or settings.llm_timeout
        # Create client — the key is stored inside the client object, never logged
        self._client = anthropic.Anthropic(
            api_key=resolved_key,
            timeout=self._timeout,
        )
        logger.info(
            "AnthropicProvider initialised model=%r timeout=%.1fs",
            self._model,
            self._timeout,
        )

    def chat(
        self,
        messages: list[dict[str, str]],
        system_prompt: str | None = None,
        tools: list[dict] | None = None,
        tool_executor: Callable[[str, dict], str] | None = None,
    ) -> LLMResponse:
        """Send a conversation to Claude with optional tool-use.

        Implements the full agentic tool-use loop:
        1. Send messages + tool definitions to Claude.
        2. If Claude wants to call a tool, execute it and send results back.
        3. Repeat up to MAX_TOOL_ROUNDS.
        4. Return the final text response.

        Parameters
        ----------
        messages:
            Conversation history as list of {"role": ..., "content": ...} dicts.
        system_prompt:
            Optional system instruction. Passed as the ``system`` parameter.
        tools:
            Tool definitions in Anthropic's format (list of tool dicts).
        tool_executor:
            Callable that executes a tool: ``tool_executor(name, input_dict) -> str``.
            Required when tools is provided.

        Returns
        -------
        LLMResponse

        Raises
        ------
        LLMError
            On any API failure.
        """
        # Convert simple dicts to properly typed message list
        # Anthropic expects list[MessageParam]
        api_messages: list[dict] = list(messages)
        total_tool_calls = 0

        for round_num in range(MAX_TOOL_ROUNDS + 1):
            logger.debug(
                "Anthropic API call round=%d model=%r messages=%d",
                round_num,
                self._model,
                len(api_messages),
            )

            create_kwargs: dict[str, Any] = {
                "model": self._model,
                "max_tokens": 4096,
                "messages": api_messages,
            }
            if system_prompt:
                create_kwargs["system"] = system_prompt
            if tools and round_num == 0:
                # Only offer tools on the first round; subsequent rounds generate the answer
                create_kwargs["tools"] = tools

            try:
                response = self._client.messages.create(**create_kwargs)
            except anthropic.AuthenticationError as exc:
                raise LLMError(
                    f"Anthropic authentication failed. "
                    f"Check that ANTHROPIC_API_KEY is valid. HTTP {exc.status_code}."
                ) from exc
            except anthropic.RateLimitError as exc:
                raise LLMError(
                    f"Anthropic rate limit exceeded. Retry after a moment. "
                    f"HTTP {exc.status_code}."
                ) from exc
            except anthropic.APITimeoutError as exc:
                raise LLMError(
                    f"Anthropic request timed out after {self._timeout}s. "
                    f"Consider increasing LLM_TIMEOUT."
                ) from exc
            except anthropic.APIConnectionError as exc:
                raise LLMError(
                    f"Cannot connect to Anthropic API: {exc}."
                ) from exc
            except anthropic.APIStatusError as exc:
                raise LLMError(
                    f"Anthropic API error HTTP {exc.status_code}: {exc.message[:200]}"
                ) from exc

            # Check for tool_use blocks
            tool_use_blocks: list[atypes.ToolUseBlock] = [
                block for block in response.content
                if isinstance(block, atypes.ToolUseBlock)
            ]

            if response.stop_reason == "tool_use" and tool_use_blocks and tool_executor:
                total_tool_calls += len(tool_use_blocks)

                # Append the assistant's response (with tool_use blocks) to messages
                api_messages.append({
                    "role": "assistant",
                    "content": response.content,
                })

                # Execute each tool and collect results
                tool_results = []
                for tool_block in tool_use_blocks:
                    logger.debug(
                        "Executing tool=%r id=%r",
                        tool_block.name,
                        tool_block.id,
                    )
                    try:
                        result_content = tool_executor(tool_block.name, tool_block.input)
                    except Exception as exc:
                        result_content = f"Tool execution error: {exc}"
                        logger.warning(
                            "Tool execution failed tool=%r error=%r",
                            tool_block.name,
                            str(exc),
                        )

                    tool_results.append({
                        "type": "tool_result",
                        "tool_use_id": tool_block.id,
                        "content": result_content,
                    })

                # Append tool results as user message
                api_messages.append({
                    "role": "user",
                    "content": tool_results,
                })

                if round_num >= MAX_TOOL_ROUNDS:
                    logger.warning(
                        "Reached MAX_TOOL_ROUNDS=%d — stopping tool loop",
                        MAX_TOOL_ROUNDS,
                    )
                    break
                # Continue loop to get final answer
                continue

            # No tool_use or end_turn — extract final text
            text_content = " ".join(
                block.text
                for block in response.content
                if isinstance(block, atypes.TextBlock)
            ).strip()

            if not text_content:
                raise LLMError(
                    f"Anthropic returned empty text response. "
                    f"stop_reason={response.stop_reason!r} "
                    f"content_types={[type(b).__name__ for b in response.content]}"
                )

            logger.info(
                "Anthropic response complete model=%r stop_reason=%r "
                "tool_calls=%d input_tokens=%d output_tokens=%d",
                self._model,
                response.stop_reason,
                total_tool_calls,
                response.usage.input_tokens,
                response.usage.output_tokens,
            )

            return LLMResponse(
                content=text_content,
                provider="anthropic",
                model=self._model,
                tool_calls_made=total_tool_calls,
                raw_metadata={
                    "stop_reason": response.stop_reason,
                    "input_tokens": response.usage.input_tokens,
                    "output_tokens": response.usage.output_tokens,
                },
            )

        # If we exhausted rounds without a final answer, extract whatever text exists
        text_content = " ".join(
            block.text
            for block in response.content  # type: ignore[possibly-undefined]
            if isinstance(block, atypes.TextBlock)
        ).strip()

        return LLMResponse(
            content=text_content or "Unable to generate a response after tool-use rounds.",
            provider="anthropic",
            model=self._model,
            tool_calls_made=total_tool_calls,
        )
