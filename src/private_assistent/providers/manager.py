from __future__ import annotations

from pathlib import Path

from private_assistent.providers.adapters import BaseModelAdapter, create_model_adapter
from private_assistent.providers.models import ModelRegistry, ModelSlot, ProviderInfo
from private_assistent.providers.registry import load_model_registry, save_default_model


class ProviderManager:
    """Small provider orchestration layer inspired by QwenPaw.

    It intentionally keeps only the responsibilities this project needs now:
    config loading, active model validation, adapter creation, and generation.
    """

    def __init__(self, config_path: Path | str | None = None) -> None:
        self.config_path = Path(config_path).expanduser() if config_path else None

    def load_registry(self) -> ModelRegistry:
        return load_model_registry(self.config_path)

    def get_active_model(self) -> ModelSlot:
        return self.load_registry().default_model

    def get_active_provider(self) -> ProviderInfo:
        registry = self.load_registry()
        return registry.get_provider(registry.default_model.provider_id)

    def set_active_model(self, slot: ModelSlot) -> ModelRegistry:
        return save_default_model(slot, self.config_path)

    def get_active_adapter(self) -> BaseModelAdapter:
        registry = self.load_registry()
        slot = registry.default_model
        provider = registry.get_provider(slot.provider_id)
        registry.validate_slot(slot, require_enabled=True)
        return create_model_adapter(provider, slot.model)

    async def generate(self, message: str) -> str:
        return await self.get_active_adapter().generate(message)

    async def generate_messages(self, messages: list[dict[str, str]]) -> str:
        return await self.get_active_adapter().generate_messages(messages)

    def generate_sync(self, message: str) -> str:
        return self.get_active_adapter().generate_sync(message)

    def generate_messages_sync(self, messages: list[dict[str, str]]) -> str:
        return self.get_active_adapter().generate_messages_sync(messages)
