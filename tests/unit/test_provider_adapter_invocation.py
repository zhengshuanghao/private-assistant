
import asyncio
import json

import httpx
import pytest

from private_assistent.providers.adapters import (
    AnthropicMessagesAdapter,
    GeminiAdapter,
    ModelAdapterConfig,
    OpenAIChatAdapter,
    OpenAIResponsesAdapter,
)
from private_assistent.providers.models import ProviderRuntimeError


def test_openai_chat_adapter_invokes_chat_completions(monkeypatch):
    captured = {}

    async def handler(request):
        captured["url"] = str(request.url)
        captured["auth"] = request.headers.get("authorization")
        captured["body"] = json.loads(request.content)
        return httpx.Response(200, json={"choices": [{"message": {"content": "pong"}}]})

    monkeypatch.setenv("TEST_API_KEY", "secret")
    adapter = OpenAIChatAdapter(
        ModelAdapterConfig(
            provider_id="openai",
            model="gpt-test",
            protocol="openai_chat",
            base_url="https://api.example.com/v1",
            api_key_env="TEST_API_KEY",
        ),
        transport=httpx.MockTransport(handler),
    )

    result = asyncio.run(adapter.generate("ping"))

    assert result == "pong"
    assert captured["url"] == "https://api.example.com/v1/chat/completions"
    assert captured["auth"] == "Bearer secret"
    assert captured["body"]["model"] == "gpt-test"


def test_anthropic_adapter_invokes_messages(monkeypatch):
    captured = {}

    async def handler(request):
        captured["url"] = str(request.url)
        captured["key"] = request.headers.get("x-api-key")
        captured["body"] = json.loads(request.content)
        return httpx.Response(200, json={"content": [{"type": "text", "text": "pong"}]})

    monkeypatch.setenv("TEST_API_KEY", "secret")
    adapter = AnthropicMessagesAdapter(
        ModelAdapterConfig(
            provider_id="minimax",
            model="MiniMax-M2",
            protocol="anthropic",
            base_url="https://api.minimax.io/anthropic",
            api_key_env="TEST_API_KEY",
        ),
        transport=httpx.MockTransport(handler),
    )

    result = asyncio.run(adapter.generate("ping"))

    assert result == "pong"
    assert captured["url"] == "https://api.minimax.io/anthropic/v1/messages"
    assert captured["key"] == "secret"
    assert captured["body"]["model"] == "MiniMax-M2"


def test_gemini_adapter_invokes_generate_content(monkeypatch):
    captured = {}

    async def handler(request):
        captured["url"] = str(request.url)
        captured["body"] = json.loads(request.content)
        return httpx.Response(
            200,
            json={"candidates": [{"content": {"parts": [{"text": "pong"}]}}]},
        )

    monkeypatch.setenv("TEST_API_KEY", "secret")
    adapter = GeminiAdapter(
        ModelAdapterConfig(
            provider_id="gemini",
            model="gemini-test",
            protocol="gemini",
            base_url="https://generativelanguage.googleapis.com",
            api_key_env="TEST_API_KEY",
        ),
        transport=httpx.MockTransport(handler),
    )

    result = asyncio.run(adapter.generate("ping"))

    assert result == "pong"
    assert "v1beta/models/gemini-test:generateContent" in captured["url"]
    assert "key=secret" in captured["url"]


def test_openai_responses_adapter_invokes_responses(monkeypatch):
    async def handler(request):
        return httpx.Response(200, json={"output_text": "pong"})

    monkeypatch.setenv("TEST_API_KEY", "secret")
    adapter = OpenAIResponsesAdapter(
        ModelAdapterConfig(
            provider_id="openai-response",
            model="gpt-test",
            protocol="openai_responses",
            base_url="https://api.example.com/v1",
            api_key_env="TEST_API_KEY",
        ),
        transport=httpx.MockTransport(handler),
    )

    assert asyncio.run(adapter.generate("ping")) == "pong"


def test_remote_adapter_requires_api_key(monkeypatch):
    monkeypatch.delenv("MISSING_API_KEY", raising=False)
    adapter = OpenAIChatAdapter(
        ModelAdapterConfig(
            provider_id="openai",
            model="gpt-test",
            protocol="openai_chat",
            base_url="https://api.example.com/v1",
            api_key_env="MISSING_API_KEY",
        ),
    )

    with pytest.raises(ProviderRuntimeError, match="Missing API key"):
        asyncio.run(adapter.generate("ping"))


def test_config_api_key_takes_precedence_over_environment(monkeypatch):
    captured = {}

    async def handler(request):
        captured["auth"] = request.headers.get("authorization")
        return httpx.Response(200, json={"choices": [{"message": {"content": "pong"}}]})

    monkeypatch.setenv("TEST_API_KEY", "env-secret")
    adapter = OpenAIChatAdapter(
        ModelAdapterConfig(
            provider_id="openai",
            model="gpt-test",
            protocol="openai_chat",
            base_url="https://api.example.com/v1",
            api_key="config-secret",
            api_key_env="TEST_API_KEY",
        ),
        transport=httpx.MockTransport(handler),
    )

    assert asyncio.run(adapter.generate("ping")) == "pong"
    assert captured["auth"] == "Bearer config-secret"


def test_openai_chat_adapter_invokes_chat_completions_with_context(monkeypatch):
    captured = {}

    async def handler(request):
        captured["body"] = json.loads(request.content)
        return httpx.Response(200, json={"choices": [{"message": {"content": "context pong"}}]})

    monkeypatch.setenv("TEST_API_KEY", "secret")
    adapter = OpenAIChatAdapter(
        ModelAdapterConfig(
            provider_id="openai",
            model="gpt-test",
            protocol="openai_chat",
            base_url="https://api.example.com/v1",
            api_key_env="TEST_API_KEY",
        ),
        transport=httpx.MockTransport(handler),
    )

    result = asyncio.run(
        adapter.generate_messages(
            [
                {"role": "user", "content": "first"},
                {"role": "assistant", "content": "second"},
                {"role": "user", "content": "third"},
            ],
        ),
    )

    assert result == "context pong"
    assert captured["body"]["messages"] == [
        {"role": "user", "content": "first"},
        {"role": "assistant", "content": "second"},
        {"role": "user", "content": "third"},
    ]
