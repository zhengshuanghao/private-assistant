from pathlib import Path

import yaml

from private_assistent.config import get_settings
from private_assistent.config.paths import bootstrap_runtime_home
from private_assistent.providers import load_model_registry
from private_assistent.providers.catalog import BUILTIN_PROVIDER_IDS


def test_bootstrap_runtime_home_creates_config_and_data_dirs(tmp_path, monkeypatch):
    working_dir = tmp_path / "runtime-home"
    monkeypatch.setenv("PRIVATE_ASSISTENT_WORKING_DIR", str(working_dir))
    get_settings.cache_clear()

    config_path = bootstrap_runtime_home()

    assert config_path == working_dir / "config.yaml"
    assert config_path.exists()
    assert (working_dir / "providers").is_dir()
    assert (working_dir / "data" / "workspace").is_dir()
    assert (working_dir / "data" / "memory").is_dir()
    assert (working_dir / "data" / "sessions").is_dir()
    assert (working_dir / "logs").is_dir()

    config = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    assert config["default_model"] == {"provider_id": "local", "model": "qwen-local"}
    assert config["providers"]["local"]["enabled"] is True
    assert config["providers"]["openai"]["enabled"] is False


def test_load_model_registry_bootstraps_all_builtin_providers(tmp_path, monkeypatch):
    working_dir = tmp_path / "runtime-home"
    monkeypatch.setenv("PRIVATE_ASSISTENT_WORKING_DIR", str(working_dir))
    get_settings.cache_clear()

    registry = load_model_registry()

    provider_ids = {provider.id for provider in registry.providers}
    assert set(BUILTIN_PROVIDER_IDS).issubset(provider_ids)
    assert registry.default_model.provider_id == "local"
    assert registry.get_provider("openai").api_key_env == "OPENAI_API_KEY"
    assert registry.get_provider("openai").enabled is False
    assert registry.get_provider("ollama").require_api_key is False
    assert [provider.id for provider in registry.enabled_providers()] == ["local"]


def test_explicit_config_path_is_bootstrapped_without_using_working_dir(tmp_path, monkeypatch):
    working_dir = tmp_path / "working-dir"
    config_path = tmp_path / "custom" / "providers.yaml"
    monkeypatch.setenv("PRIVATE_ASSISTENT_WORKING_DIR", str(working_dir))
    monkeypatch.setenv("PRIVATE_ASSISTENT_CONFIG_PATH", str(config_path))
    get_settings.cache_clear()

    registry = load_model_registry()

    assert config_path.exists()
    assert not (working_dir / "config.yaml").exists()
    assert registry.get_provider("gemini").api_key_env == "GOOGLE_API_KEY"
