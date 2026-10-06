
import pytest
import yaml

from private_assistent.providers.manager import ProviderManager
from private_assistent.providers.models import ModelSlot, ProviderConfigError


def write_config(path):
    path.write_text(
        yaml.safe_dump(
            {
                "providers": {
                    "local": {
                        "name": "Local",
                        "protocol": "local",
                        "require_api_key": False,
                        "models": [{"id": "qwen-local", "name": "Qwen Local"}],
                    },
                    "openai": {
                        "name": "OpenAI",
                        "protocol": "openai_chat",
                        "enabled": True,
                        "base_url": "https://api.openai.test/v1",
                        "api_key_env": "OPENAI_API_KEY",
                        "models": [{"id": "gpt-test", "name": "GPT Test"}],
                    },
                },
                "default_model": {"provider_id": "local", "model": "qwen-local"},
            },
            sort_keys=False,
        ),
        encoding="utf-8",
    )


def test_provider_manager_reads_and_updates_default_model(tmp_path):
    config_path = tmp_path / "config.yaml"
    write_config(config_path)
    manager = ProviderManager(config_path)

    assert manager.get_active_model() == ModelSlot(provider_id="local", model="qwen-local")

    updated = manager.set_active_model(ModelSlot(provider_id="openai", model="gpt-test"))

    assert updated.default_model == ModelSlot(provider_id="openai", model="gpt-test")
    assert manager.get_active_provider().id == "openai"


def test_provider_manager_builds_active_adapter(tmp_path):
    config_path = tmp_path / "config.yaml"
    write_config(config_path)
    manager = ProviderManager(config_path)
    manager.set_active_model(ModelSlot(provider_id="openai", model="gpt-test"))

    adapter = manager.get_active_adapter()

    assert adapter.config.provider_id == "openai"
    assert adapter.config.model == "gpt-test"
    assert adapter.config.protocol == "openai_chat"


def test_provider_manager_refuses_disabled_default(tmp_path):
    config_path = tmp_path / "config.yaml"
    write_config(config_path)
    data = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    data["providers"]["openai"]["enabled"] = False
    config_path.write_text(yaml.safe_dump(data), encoding="utf-8")
    manager = ProviderManager(config_path)

    with pytest.raises(ProviderConfigError, match="not enabled"):
        manager.set_active_model(ModelSlot(provider_id="openai", model="gpt-test"))
