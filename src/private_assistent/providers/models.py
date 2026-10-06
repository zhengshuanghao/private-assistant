from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field, field_validator, model_validator

from private_assistent.providers.protocols import (
    SUPPORTED_PROVIDER_PROTOCOLS,
    infer_protocol,
)


class ProviderConfigError(ValueError):
    """Raised when provider configuration is invalid."""


class ProviderRuntimeError(RuntimeError):
    """Raised when a configured provider cannot be invoked."""


class ModelInfo(BaseModel):
    id: str = Field(min_length=1)
    name: str = Field(min_length=1)


class ModelSlot(BaseModel):
    provider_id: str = Field(min_length=1)
    model: str = Field(min_length=1)


class ProviderInfo(BaseModel):
    id: str = Field(min_length=1)
    name: str = Field(min_length=1)
    type: str = Field(default="openai_compatible", min_length=1)
    protocol: str = ""
    category: str = Field(default="cloud", min_length=1)
    base_url: str = ""
    api_key: str = ""
    api_key_env: str = ""
    require_api_key: bool = True
    enabled: bool = True
    models: list[ModelInfo] = Field(default_factory=list)
    generate_kwargs: dict[str, Any] = Field(default_factory=dict)
    custom_headers: dict[str, str] = Field(default_factory=dict)

    @model_validator(mode="after")
    def normalize_protocol(self) -> "ProviderInfo":
        self.protocol = infer_protocol(self.protocol, self.type, self.id)
        if self.protocol not in SUPPORTED_PROVIDER_PROTOCOLS:
            raise ProviderConfigError(
                f"Unsupported provider protocol: {self.protocol}",
            )
        return self

    @field_validator("models")
    @classmethod
    def require_models(cls, value: list[ModelInfo]) -> list[ModelInfo]:
        if not value:
            raise ValueError("provider must define at least one model")
        return value

    def has_model(self, model_id: str) -> bool:
        return any(model.id == model_id for model in self.models)


class ModelRegistry(BaseModel):
    providers: list[ProviderInfo]
    default_model: ModelSlot

    def get_provider(self, provider_id: str) -> ProviderInfo:
        for provider in self.providers:
            if provider.id == provider_id:
                return provider
        raise ProviderConfigError(f"Unknown provider: {provider_id}")

    def validate_slot(self, slot: ModelSlot, *, require_enabled: bool = False) -> None:
        provider = self.get_provider(slot.provider_id)
        if require_enabled and not provider.enabled:
            raise ProviderConfigError(
                f"Provider '{slot.provider_id}' is not enabled in user config",
            )
        if not provider.has_model(slot.model):
            raise ProviderConfigError(
                f"Unknown model '{slot.model}' for provider '{slot.provider_id}'",
            )

    def enabled_providers(self) -> list[ProviderInfo]:
        return [provider for provider in self.providers if provider.enabled]
