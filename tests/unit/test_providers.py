from pathlib import Path

import pytest
import yaml

from private_assistent.providers.registry import (
    ModelSlot,
    ProviderConfigError,
    load_model_registry,
    save_default_model,
)


def write_config(path: Path) -> None:
    path.write_text(
        yaml.safe_dump(
            {
                "providers": {
                    "ollama": {
                        "name": "Ollama",
                        "type": "openai_compatible",
                        "base_url": "http://127.0.0.1:11434/v1",
                        "models": [
                            {"id": "qwen2.5:7b", "name": "Qwen 2.5 7B"},
                            {"id": "llama3.1:8b", "name": "Llama 3.1 8B"},
                        ],
                    },
                    "openai": {
                        "name": "OpenAI",
                        "type": "openai",
                        "base_url": "https://api.openai.com/v1",
                        "api_key_env": "OPENAI_API_KEY",
                        "models": [
                            {"id": "gpt-4.1-mini", "name": "GPT-4.1 Mini"},
                        ],
                    },
                },
                "default_model": {
                    "provider_id": "ollama",
                    "model": "qwen2.5:7b",
                },
            },
            allow_unicode=True,
            sort_keys=False,
        ),
        encoding="utf-8",
    )


def test_load_model_registry_supports_multiple_providers(tmp_path):
    config_path = tmp_path / "default.yaml"
    write_config(config_path)

    registry = load_model_registry(config_path)

    assert registry.default_model == ModelSlot(
        provider_id="ollama",
        model="qwen2.5:7b",
    )
    assert [provider.id for provider in registry.providers] == ["ollama", "openai"]
    assert registry.get_provider("openai").models[0].id == "gpt-4.1-mini"


def test_load_model_registry_rejects_unknown_default_model(tmp_path):
    config_path = tmp_path / "default.yaml"
    write_config(config_path)
    data = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    data["default_model"] = {"provider_id": "openai", "model": "missing"}
    config_path.write_text(yaml.safe_dump(data), encoding="utf-8")

    with pytest.raises(ProviderConfigError):
        load_model_registry(config_path)


def test_save_default_model_persists_valid_selection(tmp_path):
    config_path = tmp_path / "default.yaml"
    write_config(config_path)

    updated = save_default_model(
        ModelSlot(provider_id="openai", model="gpt-4.1-mini"),
        config_path,
    )

    assert updated.default_model.provider_id == "openai"
    assert load_model_registry(config_path).default_model.model == "gpt-4.1-mini"


def test_save_default_model_rejects_disabled_provider(tmp_path):
    config_path = tmp_path / "default.yaml"
    write_config(config_path)
    data = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    data["providers"]["openai"]["enabled"] = False
    config_path.write_text(yaml.safe_dump(data), encoding="utf-8")

    with pytest.raises(ProviderConfigError, match="not enabled"):
        save_default_model(
            ModelSlot(provider_id="openai", model="gpt-4.1-mini"),
            config_path,
        )
