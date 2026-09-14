"""Ollama LLM provider using the /api/chat endpoint with tool-use support.

Ollama tool-use
---------------
Ollama's /api/chat endpoint supports a ``tools`` parameter that mirrors
OpenAI function-calling format. When the model wants to call a tool,
it returns a response with ``message.tool_calls`` instead of plain text.

Agent loop
----------
1. POST /api/chat with messages + tool definitions + stream=false.
2. If response contains tool_calls:
   a. Execute each tool via tool_executor.
   b. Append assistant message + tool result messages.
   c. POST /api/chat again (without tools) to get the final answer.
3. Return LLMResponse.

If the Ollama model does not support tool-use (older models), the response
will simply be text. The grounding then relies on the system prompt
injecting the retrieved context as plain text (fallback strategy).

Failure Modes
-------------
- Ollama unavailable → LLMError with actionable message.
- Timeout → LLMError.
- Non-200 response → LLMError with status.
- Never silently falls back to Anthropic.
"""

from __future__ import annotations

import json
import logging
from typing import Any, Callable

import httpx

from app.core.config import settings
from app.llm.base import LLMError, LLMResponse

logger = logging.getLogger(__name__)

MAX_TOOL_ROUNDS = 3


class OllamaProvider:
    """LLM provider backed by a local Ollama instance.

    Uses Ollama's /api/chat endpoint. Supports tool-use for models that
    implement it (e.g. llama3.1:8b). Falls back gracefully for models
    that don't support tool-use by relying on system-prompt-injected context.

    Parameters
    ----------
    base_url:
        Ollama base URL. Defaults to settings.ollama_base_url.
    model:
        Ollama model name. Defaults to settings.ollama_model.
    timeout:
        Request timeout in seconds. Defaults to settings.llm_timeout.
    """

    def __init__(
        self,
        base_url: str | None = None,
        model: str | None = None,
        timeout: float | None = None,
    ) -> None:
        self._base_url = (base_url or settings.ollama_base_url).rstrip("/")
        self._model = model or settings.ollama_model
        self._timeout = timeout or settings.llm_timeout
        logger.info(
            "OllamaProvider initialised base_url=%r model=%r timeout=%.1fs",
            self._base_url,
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
        """Send conversation to Ollama with optional tool-use.

        Parameters
        ----------
        messages:
            Conversation history as list of {"role": ..., "content": ...} dicts.
        system_prompt:
            Optional system instruction prepended as a system message.
        tools:
            Tool definitions in Ollama's format (mirrors OpenAI format).
        tool_executor:
            Callable that executes a tool: ``tool_executor(name, input_dict) -> str``.

        Returns
        -------
        LLMResponse

        Raises
        ------
        LLMError
            On connection failure, timeout, or non-200 response.
        """
        api_messages = self._build_messages(messages, system_prompt)
        total_tool_calls = 0

        for round_num in range(MAX_TOOL_ROUNDS + 1):
            payload: dict[str, Any] = {
                "model": self._model,
                "messages": api_messages,
                "stream": False,
                "options": {
                    "num_predict": settings.ollama_num_predict,
                    "temperature": settings.ollama_temperature,
                },
            }
            # Only offer tools on first round
            if tools and round_num == 0:
                payload["tools"] = tools

            logger.debug(
                "Ollama API call round=%d model=%r messages=%d",
                round_num,
                self._model,
                len(api_messages),
            )

            try:
                response = httpx.post(
                    f"{self._base_url}/api/chat",
                    json=payload,
                    timeout=self._timeout,
                )
                response.raise_for_status()
            except httpx.ConnectError as exc:
                raise LLMError(
                    f"Cannot connect to Ollama at {self._base_url}. "
                    f"Is Ollama running? Start it with: ollama serve\n"
                    f"Then pull the model: ollama pull {self._model}\n"
                    f"Original error: {exc}"
                ) from exc
            except httpx.TimeoutException as exc:
                raise LLMError(
                    f"Ollama request timed out after {self._timeout}s "
                    f"(model={self._model!r}). "
                    f"Consider increasing LLM_TIMEOUT."
                ) from exc
            except httpx.HTTPStatusError as exc:
                raise LLMError(
                    f"Ollama returned HTTP {exc.response.status_code}. "
                    f"Response: {exc.response.text[:200]}"
                ) from exc

            data = response.json()
            msg = data.get("message", {})
            tool_calls = msg.get("tool_calls", [])

            if tool_calls and tool_executor and round_num < MAX_TOOL_ROUNDS:
                total_tool_calls += len(tool_calls)

                # Append assistant message with tool_calls
                api_messages.append({
                    "role": "assistant",
                    "content": msg.get("content") or "",
                    "tool_calls": tool_calls,
                })

                # Execute each tool and append results
                for tc in tool_calls:
                    fn = tc.get("function", {})
                    tool_name = fn.get("name", "")
                    tool_args = fn.get("arguments", {})
                    if isinstance(tool_args, str):
                        try:
                            tool_args = json.loads(tool_args)
                        except json.JSONDecodeError:
                            tool_args = {}

                    logger.debug("Executing tool=%r args=%r", tool_name, tool_args)
                    try:
                        result = tool_executor(tool_name, tool_args)
                    except Exception as exc:
                        result = f"Tool execution error: {exc}"
                        logger.warning(
                            "Tool execution failed tool=%r error=%r", tool_name, str(exc)
                        )

                    api_messages.append({
                        "role": "tool",
                        "content": result,
                    })

                continue  # Get final answer

            # No tool calls — extract text content
            content = msg.get("content", "").strip()

            if not content:
                raise LLMError(
                    f"Ollama returned empty content for model {self._model!r}. "
                    f"Response keys: {list(data.keys())}"
                )

            done_reason = data.get("done_reason", "unknown")
            logger.info(
                "Ollama response complete model=%r done_reason=%r tool_calls=%d",
                self._model,
                done_reason,
                total_tool_calls,
            )

            return LLMResponse(
                content=content,
                provider="ollama",
                model=self._model,
                tool_calls_made=total_tool_calls,
                raw_metadata={
                    "done_reason": done_reason,
                    "prompt_eval_count": data.get("prompt_eval_count"),
                    "eval_count": data.get("eval_count"),
                },
            )

        # Fallback if tool rounds exhausted
        return LLMResponse(
            content="Unable to generate a response after tool-use rounds.",
            provider="ollama",
            model=self._model,
            tool_calls_made=total_tool_calls,
        )

    def _build_messages(
        self,
        messages: list[dict[str, str]],
        system_prompt: str | None,
    ) -> list[dict[str, str]]:
        """Prepend system prompt as a system message if provided."""
        if system_prompt:
            return [{"role": "system", "content": system_prompt}, *messages]
        return list(messages)
