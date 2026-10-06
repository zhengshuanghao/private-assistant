from __future__ import annotations

SUPPORTED_PROVIDER_PROTOCOLS = frozenset(
    {
        "local",
        "openai_chat",
        "anthropic",
        "gemini",
        "openai_responses",
    },
)

LEGACY_TYPE_PROTOCOLS = {
    "local": "local",
    "openai": "openai_chat",
    "openai_compatible": "openai_chat",
    "azure_openai": "openai_chat",
    "anthropic": "anthropic",
    "gemini": "gemini",
    "openai_response": "openai_responses",
    "openai_responses": "openai_responses",
}

SERVICE_PROTOCOLS = {
    "local": "local",
    "qwenpaw-local": "local",
    "ollama": "openai_chat",
    "lmstudio": "openai_chat",
    "modelscope": "openai_chat",
    "dashscope": "openai_chat",
    "openai": "openai_chat",
    "openai-response": "openai_responses",
    "azure-openai": "openai_chat",
    "anthropic": "anthropic",
    "gemini": "gemini",
    "deepseek": "openai_chat",
    "kimi-cn": "openai_chat",
    "kimi-intl": "openai_chat",
    "minimax": "anthropic",
    "minimax-cn": "anthropic",
    "zhipu-cn": "openai_chat",
    "zhipu-intl": "openai_chat",
    "siliconflow-cn": "openai_chat",
    "siliconflow-intl": "openai_chat",
    "openrouter": "openai_chat",
    "volcengine-cn": "openai_chat",
    "volcengine-cn-codingplan": "openai_chat",
    "volcengine-cn-agentplan": "openai_chat",
    "mimo": "openai_chat",
    "mimo-tokenplan": "openai_chat",
    "opencode": "openai_chat",
    "aliyun-codingplan": "openai_chat",
    "aliyun-codingplan-intl": "openai_chat",
    "aliyun-tokenplan": "openai_chat",
    "aliyun-tokenplan-intl": "openai_chat",
    "kilo": "openai_chat",
}


def infer_protocol(
    protocol: str | None = None,
    legacy_type: str | None = None,
    provider_id: str | None = None,
) -> str:
    value = (protocol or "").strip()
    if value:
        return value
    service_protocol = SERVICE_PROTOCOLS.get((provider_id or "").strip())
    if service_protocol:
        return service_protocol
    return LEGACY_TYPE_PROTOCOLS.get((legacy_type or "openai_compatible").strip(), "")
