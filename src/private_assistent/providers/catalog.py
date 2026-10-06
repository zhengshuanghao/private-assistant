from __future__ import annotations

from copy import deepcopy
from typing import Any

from private_assistent.providers.protocols import SERVICE_PROTOCOLS

BUILTIN_PROVIDER_IDS = (
    "local",
    "qwenpaw-local",
    "ollama",
    "lmstudio",
    "modelscope",
    "dashscope",
    "openai",
    "openai-response",
    "azure-openai",
    "anthropic",
    "gemini",
    "deepseek",
    "kimi-cn",
    "kimi-intl",
    "minimax",
    "minimax-cn",
    "zhipu-cn",
    "zhipu-intl",
    "siliconflow-cn",
    "siliconflow-intl",
    "openrouter",
    "volcengine-cn",
    "volcengine-cn-codingplan",
    "volcengine-cn-agentplan",
    "mimo",
    "mimo-tokenplan",
    "opencode",
    "aliyun-codingplan",
    "aliyun-codingplan-intl",
    "aliyun-tokenplan",
    "aliyun-tokenplan-intl",
    "kilo",
)

BUILTIN_PROVIDER_CATALOG: dict[str, dict[str, Any]] = {
    "local": {
        "name": "Local Placeholder",
        "type": "local",
        "category": "local",
        "require_api_key": False,
        "models": [{"id": "qwen-local", "name": "Qwen Local Placeholder"}],
    },
    "qwenpaw-local": {
        "name": "QwenPaw Local",
        "type": "local",
        "category": "local",
        "require_api_key": False,
        "models": [{"id": "qwenpaw-local", "name": "QwenPaw Local Model"}],
    },
    "ollama": {
        "name": "Ollama",
        "type": "openai_compatible",
        "category": "local",
        "base_url": "http://127.0.0.1:11434/v1",
        "require_api_key": False,
        "models": [
            {"id": "qwen2.5:7b", "name": "Qwen 2.5 7B"},
            {"id": "llama3.1:8b", "name": "Llama 3.1 8B"},
        ],
    },
    "lmstudio": {
        "name": "LM Studio",
        "type": "openai_compatible",
        "category": "local",
        "base_url": "http://127.0.0.1:1234/v1",
        "require_api_key": False,
        "models": [{"id": "local-model", "name": "LM Studio Loaded Model"}],
    },
    "modelscope": {
        "name": "ModelScope",
        "type": "openai_compatible",
        "base_url": "https://api-inference.modelscope.cn/v1",
        "api_key_env": "MODELSCOPE_API_KEY",
        "models": [{"id": "Qwen/Qwen3-Coder-480B-A35B-Instruct", "name": "Qwen3 Coder"}],
    },
    "dashscope": {
        "name": "DashScope",
        "type": "openai_compatible",
        "base_url": "https://dashscope.aliyuncs.com/compatible-mode/v1",
        "api_key_env": "DASHSCOPE_API_KEY",
        "models": [
            {"id": "qwen-plus", "name": "Qwen Plus"},
            {"id": "qwen-max", "name": "Qwen Max"},
        ],
    },
    "openai": {
        "name": "OpenAI",
        "type": "openai",
        "base_url": "https://api.openai.com/v1",
        "api_key_env": "OPENAI_API_KEY",
        "models": [
            {"id": "gpt-4.1-mini", "name": "GPT-4.1 Mini"},
            {"id": "gpt-4.1", "name": "GPT-4.1"},
        ],
    },
    "openai-response": {
        "name": "OpenAI Responses",
        "type": "openai_response",
        "base_url": "https://api.openai.com/v1",
        "api_key_env": "OPENAI_API_KEY",
        "models": [{"id": "gpt-4.1-mini", "name": "GPT-4.1 Mini"}],
    },
    "azure-openai": {
        "name": "Azure OpenAI",
        "type": "azure_openai",
        "api_key_env": "AZURE_OPENAI_API_KEY",
        "models": [{"id": "deployment-name", "name": "Azure Deployment Name"}],
        "generate_kwargs": {"api_version": "2024-10-21"},
    },
    "anthropic": {
        "name": "Anthropic",
        "type": "anthropic",
        "base_url": "https://api.anthropic.com",
        "api_key_env": "ANTHROPIC_API_KEY",
        "models": [
            {"id": "claude-sonnet-4-5", "name": "Claude Sonnet 4.5"},
            {"id": "claude-3-5-haiku-latest", "name": "Claude 3.5 Haiku"},
        ],
    },
    "gemini": {
        "name": "Google Gemini",
        "type": "gemini",
        "base_url": "https://generativelanguage.googleapis.com",
        "api_key_env": "GOOGLE_API_KEY",
        "models": [
            {"id": "gemini-2.5-flash", "name": "Gemini 2.5 Flash"},
            {"id": "gemini-2.5-pro", "name": "Gemini 2.5 Pro"},
        ],
    },
    "deepseek": {
        "name": "DeepSeek",
        "type": "openai_compatible",
        "base_url": "https://api.deepseek.com/v1",
        "api_key_env": "DEEPSEEK_API_KEY",
        "models": [{"id": "deepseek-chat", "name": "DeepSeek Chat"}],
    },
    "kimi-cn": {
        "name": "Kimi CN",
        "type": "openai_compatible",
        "base_url": "https://api.moonshot.cn/v1",
        "api_key_env": "MOONSHOT_API_KEY",
        "models": [{"id": "kimi-k2-0711-preview", "name": "Kimi K2"}],
    },
    "kimi-intl": {
        "name": "Kimi International",
        "type": "openai_compatible",
        "base_url": "https://api.moonshot.ai/v1",
        "api_key_env": "MOONSHOT_API_KEY",
        "models": [{"id": "kimi-k2-0711-preview", "name": "Kimi K2"}],
    },
    "minimax": {
        "name": "MiniMax International",
        "type": "anthropic",
        "base_url": "https://api.minimax.io/anthropic",
        "api_key_env": "MINIMAX_API_KEY",
        "models": [{"id": "MiniMax-M1", "name": "MiniMax M1"}],
    },
    "minimax-cn": {
        "name": "MiniMax CN",
        "type": "anthropic",
        "base_url": "https://api.minimaxi.com/anthropic",
        "api_key_env": "MINIMAX_API_KEY",
        "models": [{"id": "MiniMax-M1", "name": "MiniMax M1"}],
    },
    "zhipu-cn": {
        "name": "Zhipu CN",
        "type": "openai_compatible",
        "base_url": "https://open.bigmodel.cn/api/paas/v4",
        "api_key_env": "ZHIPU_API_KEY",
        "models": [{"id": "glm-4-plus", "name": "GLM-4 Plus"}],
    },
    "zhipu-intl": {
        "name": "Zhipu International",
        "type": "openai_compatible",
        "base_url": "https://open.bigmodel.cn/api/paas/v4",
        "api_key_env": "ZHIPU_API_KEY",
        "models": [{"id": "glm-4-plus", "name": "GLM-4 Plus"}],
    },
    "siliconflow-cn": {
        "name": "SiliconFlow CN",
        "type": "openai_compatible",
        "base_url": "https://api.siliconflow.cn/v1",
        "api_key_env": "SILICONFLOW_API_KEY",
        "models": [{"id": "Qwen/Qwen2.5-72B-Instruct", "name": "Qwen 2.5 72B"}],
    },
    "siliconflow-intl": {
        "name": "SiliconFlow International",
        "type": "openai_compatible",
        "base_url": "https://api.siliconflow.com/v1",
        "api_key_env": "SILICONFLOW_API_KEY",
        "models": [{"id": "Qwen/Qwen2.5-72B-Instruct", "name": "Qwen 2.5 72B"}],
    },
    "openrouter": {
        "name": "OpenRouter",
        "type": "openai_compatible",
        "base_url": "https://openrouter.ai/api/v1",
        "api_key_env": "OPENROUTER_API_KEY",
        "models": [{"id": "openrouter/auto", "name": "OpenRouter Auto"}],
    },
    "volcengine-cn": {
        "name": "Volcengine CN",
        "type": "openai_compatible",
        "base_url": "https://ark.cn-beijing.volces.com/api/v3",
        "api_key_env": "VOLCENGINE_API_KEY",
        "models": [{"id": "doubao-seed-1-6", "name": "Doubao Seed 1.6"}],
    },
    "volcengine-cn-codingplan": {
        "name": "Volcengine CN Coding Plan",
        "type": "openai_compatible",
        "base_url": "https://ark.cn-beijing.volces.com/api/v3",
        "api_key_env": "VOLCENGINE_API_KEY",
        "models": [{"id": "doubao-seed-1-6", "name": "Doubao Seed 1.6"}],
    },
    "volcengine-cn-agentplan": {
        "name": "Volcengine CN Agent Plan",
        "type": "openai_compatible",
        "base_url": "https://ark.cn-beijing.volces.com/api/v3",
        "api_key_env": "VOLCENGINE_API_KEY",
        "models": [{"id": "doubao-seed-1-6", "name": "Doubao Seed 1.6"}],
    },
    "mimo": {
        "name": "Mimo",
        "type": "openai_compatible",
        "api_key_env": "MIMO_API_KEY",
        "models": [{"id": "mimo-chat", "name": "Mimo Chat"}],
    },
    "mimo-tokenplan": {
        "name": "Mimo Token Plan",
        "type": "openai_compatible",
        "api_key_env": "MIMO_API_KEY",
        "models": [{"id": "mimo-chat", "name": "Mimo Chat"}],
    },
    "opencode": {
        "name": "OpenCode",
        "type": "openai_compatible",
        "api_key_env": "OPENCODE_API_KEY",
        "models": [{"id": "opencode/default", "name": "OpenCode Default"}],
    },
    "aliyun-codingplan": {
        "name": "Aliyun Coding Plan",
        "type": "openai_compatible",
        "base_url": "https://dashscope.aliyuncs.com/compatible-mode/v1",
        "api_key_env": "DASHSCOPE_API_KEY",
        "models": [{"id": "qwen3-coder-plus", "name": "Qwen3 Coder Plus"}],
    },
    "aliyun-codingplan-intl": {
        "name": "Aliyun Coding Plan International",
        "type": "openai_compatible",
        "base_url": "https://dashscope-intl.aliyuncs.com/compatible-mode/v1",
        "api_key_env": "DASHSCOPE_API_KEY",
        "models": [{"id": "qwen3-coder-plus", "name": "Qwen3 Coder Plus"}],
    },
    "aliyun-tokenplan": {
        "name": "Aliyun Token Plan",
        "type": "openai_compatible",
        "base_url": "https://dashscope.aliyuncs.com/compatible-mode/v1",
        "api_key_env": "DASHSCOPE_API_KEY",
        "models": [{"id": "qwen-plus", "name": "Qwen Plus"}],
    },
    "aliyun-tokenplan-intl": {
        "name": "Aliyun Token Plan International",
        "type": "openai_compatible",
        "base_url": "https://dashscope-intl.aliyuncs.com/compatible-mode/v1",
        "api_key_env": "DASHSCOPE_API_KEY",
        "models": [{"id": "qwen-plus", "name": "Qwen Plus"}],
    },
    "kilo": {
        "name": "Kilo Code",
        "type": "openai_compatible",
        "api_key_env": "KILO_API_KEY",
        "models": [{"id": "kilo/default", "name": "Kilo Default"}],
    },
}


def build_default_config() -> dict[str, Any]:
    providers = deepcopy(BUILTIN_PROVIDER_CATALOG)
    for provider_id, provider in providers.items():
        provider["enabled"] = provider_id == "local"
        provider["protocol"] = SERVICE_PROTOCOLS[provider_id]

    return {
        "app": {"name": "Private Assistent", "host": "127.0.0.1", "port": 8088},
        "providers": providers,
        "default_model": {"provider_id": "local", "model": "qwen-local"},
        "paths": {
            "workspace": "data/workspace",
            "memory": "data/memory",
            "sessions": "data/sessions",
        },
        "security": {"require_tool_approval": True},
    }
