from __future__ import annotations

import asyncio
import os
from dataclasses import dataclass, field
from typing import Any, TYPE_CHECKING
from urllib.parse import quote

import httpx

from private_assistent.providers.models import ProviderRuntimeError
from private_assistent.providers.protocols import SUPPORTED_PROVIDER_PROTOCOLS

if TYPE_CHECKING:
    from private_assistent.providers.models import ProviderInfo


@dataclass(frozen=True)
class ModelAdapterConfig:
    provider_id: str
    model: str
    protocol: str
    base_url: str = ""
    api_key: str = ""
    api_key_env: str = ""
    require_api_key: bool = True
    generate_kwargs: dict[str, Any] = field(default_factory=dict)
    custom_headers: dict[str, str] = field(default_factory=dict)


class BaseModelAdapter:
    protocol = ""

    def __init__(
        self,
        config: ModelAdapterConfig,
        *,
        transport: httpx.AsyncBaseTransport | None = None,
    ) -> None:
        self.config = config
        self._transport = transport

    def describe(self) -> dict[str, Any]:
        return {
            "provider_id": self.config.provider_id,
            "model": self.config.model,
            "protocol": self.config.protocol,
            "base_url": self.config.base_url,
            "has_api_key": bool(self.config.api_key),
            "api_key_env": self.config.api_key_env,
            "require_api_key": self.config.require_api_key,
        }

    async def generate(self, message: str) -> str:
        return await self.generate_messages([{"role": "user", "content": message}])

    async def generate_messages(self, messages: list[dict[str, str]]) -> str:
        raise ProviderRuntimeError(
            f"Protocol '{self.config.protocol}' is not implemented yet",
        )

    def generate_sync(self, message: str) -> str:
        try:
            asyncio.get_running_loop()
        except RuntimeError:
            return asyncio.run(self.generate(message))
        raise ProviderRuntimeError("generate_sync cannot run inside an active event loop")

    def generate_messages_sync(self, messages: list[dict[str, str]]) -> str:
        try:
            asyncio.get_running_loop()
        except RuntimeError:
            return asyncio.run(self.generate_messages(messages))
        raise ProviderRuntimeError(
            "generate_messages_sync cannot run inside an active event loop",
        )

    @staticmethod
    def _normal_messages(messages: list[dict[str, str]]) -> list[dict[str, str]]:
        normalized: list[dict[str, str]] = []
        for item in messages:
            role = str(item.get("role", "user")).strip() or "user"
            content = str(item.get("content", "")).strip()
            if role not in {"system", "user", "assistant"} or not content:
                continue
            normalized.append({"role": role, "content": content})
        if not normalized:
            raise ProviderRuntimeError("No non-empty messages to send")
        return normalized

    def _api_key(self) -> str:
        explicit = self.config.api_key.strip()
        if explicit:
            return explicit
        if not self.config.api_key_env:
            if self.config.require_api_key:
                raise ProviderRuntimeError(
                    f"Provider '{self.config.provider_id}' requires api_key or api_key_env",
                )
            return ""
        value = os.environ.get(self.config.api_key_env, "").strip()
        if self.config.require_api_key and not value:
            raise ProviderRuntimeError(
                f"Missing API key environment variable: {self.config.api_key_env}",
            )
        return value

    def _base_url(self) -> str:
        value = self.config.base_url.strip().rstrip("/")
        if not value:
            raise ProviderRuntimeError(
                f"Provider '{self.config.provider_id}' requires base_url",
            )
        return value

    def _headers(self, **extra: str) -> dict[str, str]:
        headers = dict(self.config.custom_headers)
        headers.update({key: value for key, value in extra.items() if value})
        return headers

    async def _post_json(
        self,
        url: str,
        payload: dict[str, Any],
        headers: dict[str, str],
    ) -> dict[str, Any]:
        async with httpx.AsyncClient(transport=self._transport, timeout=60) as client:
            response = await client.post(url, json=payload, headers=headers)
            try:
                response.raise_for_status()
            except httpx.HTTPStatusError as exc:
                detail = response.text[:500]
                raise ProviderRuntimeError(
                    f"Provider '{self.config.provider_id}' returned "
                    f"HTTP {response.status_code}: {detail}",
                ) from exc
            data = response.json()
            if not isinstance(data, dict):
                raise ProviderRuntimeError("Provider returned non-object JSON")
            return data


class LocalModelAdapter(BaseModelAdapter):
    protocol = "local"

    async def generate_messages(self, messages: list[dict[str, str]]) -> str:
        normalized = self._normal_messages(messages)
        message = next(
            (item["content"] for item in reversed(normalized) if item["role"] == "user"),
            normalized[-1]["content"],
        )
        return (
            f"[local placeholder] received: {message}\n"
            f"context_messages={len(normalized)}\n"
            f"model={self.config.provider_id}/{self.config.model}\n"
            f"provider_protocol={self.config.protocol}"
        )


class OpenAIChatAdapter(BaseModelAdapter):
    protocol = "openai_chat"

    async def generate_messages(self, messages: list[dict[str, str]]) -> str:
        api_key = self._api_key()
        payload = {
            "model": self.config.model,
            "messages": self._normal_messages(messages),
            **self.config.generate_kwargs,
        }
        data = await self._post_json(
            f"{self._base_url()}/chat/completions",
            payload,
            self._headers(Authorization=f"Bearer {api_key}"),
        )
        try:
            return str(data["choices"][0]["message"]["content"] or "")
        except (KeyError, IndexError, TypeError) as exc:
            raise ProviderRuntimeError("Invalid OpenAI chat response") from exc


class AnthropicMessagesAdapter(BaseModelAdapter):
    protocol = "anthropic"

    async def generate_messages(self, messages: list[dict[str, str]]) -> str:
        api_key = self._api_key()
        normalized = self._normal_messages(messages)
        system_messages = [item["content"] for item in normalized if item["role"] == "system"]
        chat_messages = [
            item for item in normalized if item["role"] in {"user", "assistant"}
        ]
        if not chat_messages:
            raise ProviderRuntimeError("Anthropic messages require user or assistant content")
        payload = {
            "model": self.config.model,
            "max_tokens": self.config.generate_kwargs.get("max_tokens", 1024),
            "messages": chat_messages,
            **({"system": "\n\n".join(system_messages)} if system_messages else {}),
            **{
                key: value
                for key, value in self.config.generate_kwargs.items()
                if key != "max_tokens"
            },
        }
        data = await self._post_json(
            self._messages_url(),
            payload,
            self._headers(
                **{
                    "x-api-key": api_key,
                    "anthropic-version": "2023-06-01",
                },
            ),
        )
        try:
            parts = data["content"]
            return "".join(
                str(part.get("text", ""))
                for part in parts
                if isinstance(part, dict) and part.get("type") == "text"
            )
        except (KeyError, TypeError) as exc:
            raise ProviderRuntimeError("Invalid Anthropic response") from exc

    def _messages_url(self) -> str:
        base = self._base_url()
        if base.endswith("/messages"):
            return base
        if base.endswith("/v1"):
            return f"{base}/messages"
        return f"{base}/v1/messages"


class GeminiAdapter(BaseModelAdapter):
    protocol = "gemini"

    async def generate_messages(self, messages: list[dict[str, str]]) -> str:
        api_key = self._api_key()
        contents = []
        for item in self._normal_messages(messages):
            role = "model" if item["role"] == "assistant" else "user"
            text = item["content"]
            if item["role"] == "system":
                text = f"System instruction:\n{text}"
            contents.append({"role": role, "parts": [{"text": text}]})
        payload = {
            "contents": contents,
            **self.config.generate_kwargs,
        }
        model = quote(self.config.model, safe="")
        data = await self._post_json(
            f"{self._base_url()}/v1beta/models/{model}:generateContent?key={api_key}",
            payload,
            self._headers(),
        )
        try:
            parts = data["candidates"][0]["content"]["parts"]
            return "".join(
                str(part.get("text", ""))
                for part in parts
                if isinstance(part, dict)
            )
        except (KeyError, IndexError, TypeError) as exc:
            raise ProviderRuntimeError("Invalid Gemini response") from exc


class OpenAIResponsesAdapter(BaseModelAdapter):
    protocol = "openai_responses"

    async def generate_messages(self, messages: list[dict[str, str]]) -> str:
        api_key = self._api_key()
        payload = {
            "model": self.config.model,
            "input": self._normal_messages(messages),
            **self.config.generate_kwargs,
        }
        data = await self._post_json(
            f"{self._base_url()}/responses",
            payload,
            self._headers(Authorization=f"Bearer {api_key}"),
        )
        if data.get("output_text") is not None:
            return str(data["output_text"])
        try:
            for item in data.get("output", []):
                for part in item.get("content", []):
                    if part.get("type") == "output_text":
                        return str(part.get("text", ""))
        except AttributeError as exc:
            raise ProviderRuntimeError("Invalid OpenAI Responses response") from exc
        raise ProviderRuntimeError("OpenAI Responses output did not include text")


_ADAPTERS: dict[str, type[BaseModelAdapter]] = {
    LocalModelAdapter.protocol: LocalModelAdapter,
    OpenAIChatAdapter.protocol: OpenAIChatAdapter,
    AnthropicMessagesAdapter.protocol: AnthropicMessagesAdapter,
    GeminiAdapter.protocol: GeminiAdapter,
    OpenAIResponsesAdapter.protocol: OpenAIResponsesAdapter,
}


def create_model_adapter(
    provider: ProviderInfo,
    model_id: str,
    *,
    transport: httpx.AsyncBaseTransport | None = None,
) -> BaseModelAdapter:
    adapter_type = _ADAPTERS.get(provider.protocol)
    if adapter_type is None:
        from private_assistent.providers.models import ProviderConfigError

        raise ProviderConfigError(
            f"Unsupported provider protocol: {provider.protocol}",
        )
    return adapter_type(
        ModelAdapterConfig(
            provider_id=provider.id,
            model=model_id,
            protocol=provider.protocol,
            base_url=provider.base_url,
            api_key=provider.api_key,
            api_key_env=provider.api_key_env,
            require_api_key=provider.require_api_key,
            generate_kwargs=dict(provider.generate_kwargs),
            custom_headers=dict(provider.custom_headers),
        ),
        transport=transport,
    )

