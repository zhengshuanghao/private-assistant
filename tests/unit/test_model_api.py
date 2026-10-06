import yaml
from fastapi.testclient import TestClient

from private_assistent.api.app import app
from private_assistent.config import get_settings


def test_model_api_lists_providers_and_switches_default(tmp_path, monkeypatch):
    config_path = tmp_path / "default.yaml"
    config_path.write_text(
        yaml.safe_dump(
            {
                "providers": {
                    "local": {
                        "name": "Local",
                        "type": "local",
                        "models": [{"id": "qwen-local", "name": "Qwen Local"}],
                    },
                    "openai": {
                        "name": "OpenAI",
                        "type": "openai",
                        "base_url": "https://api.openai.com/v1",
                        "models": [{"id": "gpt-4.1-mini", "name": "GPT-4.1 Mini"}],
                    },
                },
                "default_model": {"provider_id": "local", "model": "qwen-local"},
            },
            allow_unicode=True,
            sort_keys=False,
        ),
        encoding="utf-8",
    )
    get_settings.cache_clear()
    monkeypatch.setenv("PRIVATE_ASSISTENT_CONFIG_PATH", str(config_path))

    client = TestClient(app)
    providers_response = client.get("/api/providers")

    assert providers_response.status_code == 200
    body = providers_response.json()
    assert body["default_model"] == {"provider_id": "local", "model": "qwen-local"}
    assert [provider["id"] for provider in body["providers"]] == ["local", "openai"]

    update_response = client.put(
        "/api/models/default",
        json={"provider_id": "openai", "model": "gpt-4.1-mini"},
    )

    assert update_response.status_code == 200
    assert update_response.json() == {"provider_id": "openai", "model": "gpt-4.1-mini"}
    assert yaml.safe_load(config_path.read_text(encoding="utf-8"))["default_model"] == {
        "provider_id": "openai",
        "model": "gpt-4.1-mini",
    }


def test_model_api_rejects_disabled_provider(tmp_path, monkeypatch):
    config_path = tmp_path / "default.yaml"
    config_path.write_text(
        yaml.safe_dump(
            {
                "providers": {
                    "local": {
                        "name": "Local",
                        "type": "local",
                        "models": [{"id": "qwen-local", "name": "Qwen Local"}],
                    },
                    "openai": {
                        "name": "OpenAI",
                        "type": "openai",
                        "enabled": False,
                        "models": [{"id": "gpt-4.1-mini", "name": "GPT-4.1 Mini"}],
                    },
                },
                "default_model": {"provider_id": "local", "model": "qwen-local"},
            },
            allow_unicode=True,
            sort_keys=False,
        ),
        encoding="utf-8",
    )
    monkeypatch.setenv("PRIVATE_ASSISTENT_CONFIG_PATH", str(config_path))
    get_settings.cache_clear()

    client = TestClient(app)
    response = client.put(
        "/api/models/default",
        json={"provider_id": "openai", "model": "gpt-4.1-mini"},
    )

    assert response.status_code == 400
    assert "not enabled" in response.json()["detail"]
