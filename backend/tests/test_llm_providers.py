"""Tests for the LLM providers."""

import pytest
import httpx

from app.llm import LLMError
from app.llm.base import LLMResponse
from app.llm.ollama import OllamaProvider


class MockResponse:
    def __init__(self, json_data, status_code=200):
        self._json = json_data
        self.status_code = status_code

    def json(self):
        return self._json

    def raise_for_status(self):
        if self.status_code >= 400:
            request = httpx.Request("POST", "http://test")
            raise httpx.HTTPStatusError("Error", request=request, response=self)


def test_ollama_provider_basic(monkeypatch):
    """Test basic text generation with Ollama."""
    
    def mock_post(*args, **kwargs):
        return MockResponse({
            "message": {"content": "Hello!"},
            "done_reason": "stop"
        })

    monkeypatch.setattr(httpx, "post", mock_post)

    provider = OllamaProvider(base_url="http://test", model="test-model")
    resp = provider.chat([{"role": "user", "content": "Hi"}])
    
    assert resp.content == "Hello!"
    assert resp.provider == "ollama"
    assert resp.model == "test-model"
    assert resp.tool_calls_made == 0


def test_ollama_provider_tool_use(monkeypatch):
    """Test Ollama tool use loop."""
    
    call_count = 0
    
    def mock_post(*args, **kwargs):
        nonlocal call_count
        call_count += 1
        
        if call_count == 1:
            # Return tool call
            return MockResponse({
                "message": {
                    "tool_calls": [
                        {
                            "function": {
                                "name": "test_tool",
                                "arguments": '{"query": "test"}'
                            }
                        }
                    ]
                }
            })
        else:
            # Return final text
            return MockResponse({
                "message": {"content": "Tool answered!"}
            })

    monkeypatch.setattr(httpx, "post", mock_post)
    
    def executor(name, args):
        assert name == "test_tool"
        assert args == {"query": "test"}
        return "Tool result"

    provider = OllamaProvider(base_url="http://test", model="test-model")
    resp = provider.chat(
        messages=[{"role": "user", "content": "Hi"}],
        tools=[{"type": "function", "function": {"name": "test_tool"}}],
        tool_executor=executor
    )
    
    assert resp.content == "Tool answered!"
    assert resp.tool_calls_made == 1
    assert call_count == 2
