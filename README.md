# Private Assistent

A local AI all-purpose assistant prototype based on AgentScope-inspired architecture.

## Goals

- Run locally by default.
- Keep user config, conversations, memory, workspace data, and logs under an independent runtime home.
- Separate agent runtime, tools, memory, providers, API, WebUI, and security boundaries.
- Start small, then grow toward a QwenPaw-like local assistant.

## Runtime Working Directory

On startup, the app now bootstraps an independent working directory:

```text
~/.private-assistent/
  config.yaml
  providers/
  data/
    workspace/
    memory/
    sessions/
  logs/
```

Override it with the QwenPaw-style working-dir variable:

```bash
PRIVATE_ASSISTENT_WORKING_DIR=D:\Project\zsh-project\private-assistent\.local-run
```

Or point directly at a provider config file:

```bash
PRIVATE_ASSISTENT_CONFIG_PATH=D:\path\to\config.yaml
```

The repository file `configs/default.yaml` is only the seed/template. Your real editable working config is normally `~/.private-assistent/config.yaml`.

## Provider Configuration

`config.yaml` contains a `providers` map and one `default_model` slot:

```yaml
providers:
  ollama:
    name: Ollama
    protocol: openai_chat
    type: openai_compatible
    category: local
    enabled: true
    base_url: http://127.0.0.1:11434/v1
    require_api_key: false
    models:
      - id: qwen2.5:7b
        name: Qwen 2.5 7B

  minimax:
    name: MiniMax International
    protocol: anthropic
    type: anthropic
    enabled: true
    base_url: https://api.minimax.io/anthropic
    api_key: ""
    api_key_env: MINIMAX_API_KEY
    models:
      - id: MiniMax-M2
        name: MiniMax M2

default_model:
  provider_id: ollama
  model: qwen2.5:7b
```

The built-in catalog includes the QwenPaw-style provider ids: `local`, `qwenpaw-local`, `ollama`, `lmstudio`, `modelscope`, `dashscope`, `openai`, `openai-response`, `azure-openai`, `anthropic`, `gemini`, `deepseek`, `kimi-cn`, `kimi-intl`, `minimax`, `minimax-cn`, `zhipu-cn`, `zhipu-intl`, `siliconflow-cn`, `siliconflow-intl`, `openrouter`, `volcengine-cn`, `volcengine-cn-codingplan`, `volcengine-cn-agentplan`, `mimo`, `mimo-tokenplan`, `opencode`, `aliyun-codingplan`, `aliyun-codingplan-intl`, `aliyun-tokenplan`, `aliyun-tokenplan-intl`, and `kilo`.

At this stage, the app supports configuring and listing these providers, but the default model selector only shows providers with `enabled: true`. The built-in catalog is a seed/reference list; it does not mean every provider is already configured for use. To make a provider selectable, edit your runtime `config.yaml`, set `enabled: true`, and configure its real `models`, `base_url`, and required API key environment variable.

Provider routing follows the QwenPaw-style protocol-family architecture: many service providers map onto a small set of adapters. The current protocols are `local`, `openai_chat`, `anthropic`, `gemini`, and `openai_responses`. `type` is kept for compatibility and display; `protocol` is the field that decides which adapter is used.

The lightweight provider layer now has a `ProviderManager` plus real HTTP adapters for OpenAI-compatible Chat Completions, Anthropic Messages, Gemini `generateContent`, and OpenAI Responses. Provider keys can be supplied either as `api_key` directly in runtime `config.yaml` or via `api_key_env`; direct `api_key` takes precedence. Advanced QwenPaw features such as model discovery, encrypted key storage, multimodal probing, billing metadata, and AgentScope-native ChatModel wrapping are intentionally left for later slices.

## Layout

```text
src/private_assistent/
  agent/      Agent construction and behavior
  runtime/    Request/session orchestration
  tools/      Local tools exposed to the assistant
  memory/     Local memory and retrieval
  providers/  Model/provider catalog and adapters
  api/        FastAPI app
  web/        Built-in WebUI
  config/     Settings and runtime home bootstrap
  security/   Tool approval and guardrails
```

## Development

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -e .[dev]
private-assistent --help
private-assistent serve
```

Run tests:

```bash
python -m pytest tests/unit -q
```

