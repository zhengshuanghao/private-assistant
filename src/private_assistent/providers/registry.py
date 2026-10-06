from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml
from pydantic import ValidationError

from private_assistent.config import get_settings
from private_assistent.config.paths import bootstrap_runtime_home
from private_assistent.providers.models import (
    ModelInfo,
    ModelRegistry,
    ModelSlot,
    ProviderConfigError,
    ProviderInfo,
)


def _config_path(path: Path | str | None = None) -> Path:
    if path is not None:
        return Path(path).expanduser()
    return get_settings().config_path.expanduser()


def _ensure_config_exists(path: Path) -> None:
    if path.exists():
        return

    settings = get_settings()
    if path == settings.config_path.expanduser():
        bootstrap_runtime_home(settings.working_dir, path)
    else:
        bootstrap_runtime_home(config_path=path)


def _read_raw_config(path: Path) -> dict[str, Any]:
    _ensure_config_exists(path)
    data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    if not isinstance(data, dict):
        raise ProviderConfigError("Config root must be a mapping")
    return data


def _legacy_default_model(data: dict[str, Any]) -> ModelSlot | None:
    model = data.get("model")
    if not isinstance(model, dict):
        return None
    provider_id = model.get("provider")
    model_name = model.get("name")
    if isinstance(provider_id, str) and isinstance(model_name, str):
        return ModelSlot(provider_id=provider_id, model=model_name)
    return None


def load_model_registry(path: Path | str | None = None) -> ModelRegistry:
    config_path = _config_path(path)
    data = _read_raw_config(config_path)
    providers_data = data.get("providers")
    if not isinstance(providers_data, dict) or not providers_data:
        raise ProviderConfigError("Config must define at least one provider")

    providers: list[ProviderInfo] = []
    try:
        for provider_id, provider_data in providers_data.items():
            if not isinstance(provider_data, dict):
                raise ProviderConfigError(
                    f"Provider '{provider_id}' config must be a mapping",
                )
            providers.append(ProviderInfo(id=str(provider_id), **provider_data))

        raw_default = data.get("default_model")
        if isinstance(raw_default, dict):
            default_model = ModelSlot(**raw_default)
        else:
            legacy = _legacy_default_model(data)
            if legacy is None:
                raise ProviderConfigError("Config must define default_model")
            default_model = legacy
    except ValidationError as exc:
        raise ProviderConfigError(str(exc)) from exc

    registry = ModelRegistry(providers=providers, default_model=default_model)
    registry.validate_slot(registry.default_model, require_enabled=True)
    return registry


def save_default_model(
    slot: ModelSlot,
    path: Path | str | None = None,
) -> ModelRegistry:
    config_path = _config_path(path)
    registry = load_model_registry(config_path)
    registry.validate_slot(slot, require_enabled=True)

    data = _read_raw_config(config_path)
    data["default_model"] = slot.model_dump()
    config_path.write_text(
        yaml.safe_dump(data, allow_unicode=True, sort_keys=False),
        encoding="utf-8",
    )
    return load_model_registry(config_path)

