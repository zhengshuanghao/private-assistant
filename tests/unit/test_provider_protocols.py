
import pytest
import yaml
from pydantic import ValidationError

from private_assistent.providers.adapters import (
    AnthropicMessagesAdapter,
    GeminiAdapter,
    LocalModelAdapter,
    OpenAIChatAdapter,
    OpenAIResponsesAdapter,
    create_model_adapter,
)
from private_assistent.providers.registry import (
    ProviderConfigError,
    ProviderInfo,
    load_model_registry,
)


def test_provider_info_infers_protocol_from_legacy_type():
    provider = ProviderInfo(
        id="deepseek",
        name="DeepSeek",
        type="openai_compatible",
        models=[{"id": "deepseek-chat", "name": "DeepSeek Chat"}],
    )

    assert provider.protocol == "openai_chat"


def test_provider_info_rejects_unknown_protocol():
    with pytest.raises(ValidationError, match="Unsupported provider protocol"):
        ProviderInfo(
            id="bad",
            name="Bad",
            protocol="made_up",
            models=[{"id": "bad-model", "name": "Bad Model"}],
        )


def test_catalog_uses_qwenpaw_style_protocol_families(tmp_path):
    registry = load_model_registry(tmp_path / "config.yaml")

    assert registry.get_provider("deepseek").protocol == "openai_chat"
    assert registry.get_provider("kimi-cn").protocol == "openai_chat"
    assert registry.get_provider("minimax").protocol == "anthropic"
    assert registry.get_provider("minimax-cn").protocol == "anthropic"
    assert registry.get_provider("anthropic").protocol == "anthropic"
    assert registry.get_provider("gemini").protocol == "gemini"
    assert registry.get_provider("openai-response").protocol == "openai_responses"


def test_create_model_adapter_selects_protocol_adapter():
    cases = [
        (
            ProviderInfo(
                id="local",
                name="Local",
                protocol="local",
                require_api_key=False,
                models=[{"id": "qwen-local", "name": "Qwen Local"}],
            ),
            LocalModelAdapter,
        ),
        (
            ProviderInfo(
                id="openai",
                name="OpenAI",
                protocol="openai_chat",
                models=[{"id": "gpt-4.1-mini", "name": "GPT-4.1 Mini"}],
            ),
            OpenAIChatAdapter,
        ),
        (
            ProviderInfo(
                id="anthropic",
                name="Anthropic",
                protocol="anthropic",
                models=[{"id": "claude", "name": "Claude"}],
            ),
            AnthropicMessagesAdapter,
        ),
        (
            ProviderInfo(
                id="gemini",
                name="Gemini",
                protocol="gemini",
                models=[{"id": "gemini", "name": "Gemini"}],
            ),
            GeminiAdapter,
        ),
        (
            ProviderInfo(
                id="openai-response",
                name="OpenAI Responses",
                protocol="openai_responses",
                models=[{"id": "gpt", "name": "GPT"}],
            ),
            OpenAIResponsesAdapter,
        ),
    ]

    for provider, expected_type in cases:
        adapter = create_model_adapter(provider, provider.models[0].id)
        assert isinstance(adapter, expected_type)
        assert adapter.config.provider_id == provider.id
        assert adapter.config.protocol == provider.protocol


def test_load_model_registry_rejects_default_model_on_disabled_provider(tmp_path):
    config_path = tmp_path / "config.yaml"
    config_path.write_text(
        yaml.safe_dump(
            {
                "providers": {
                    "local": {
                        "name": "Local",
                        "protocol": "local",
                        "enabled": False,
                        "models": [{"id": "qwen-local", "name": "Qwen Local"}],
                    }
                },
                "default_model": {"provider_id": "local", "model": "qwen-local"},
            },
            sort_keys=False,
        ),
        encoding="utf-8",
    )

    with pytest.raises(ProviderConfigError, match="not enabled"):
        load_model_registry(config_path)
