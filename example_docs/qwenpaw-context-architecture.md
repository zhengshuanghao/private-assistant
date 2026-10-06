# QwenPaw 上下文管理架构调研

本文基于 `D:\Project\zsh-project\QwenPaw\src\qwenpaw` 的源码调研，目标是理解 QwenPaw 如何做上下文、历史、压缩、召回和长期记忆管理，并提炼出 `private-assistent` 后续可落地的设计方向。

## 结论摘要

QwenPaw 的上下文体系不是简单地把历史消息塞进 prompt，而是分成两条主线：

1. **Context / Scroll 上下文窗口管理**：负责当前会话的 live context、超过窗口后的压缩、被压缩内容的可召回索引，以及模型上下文溢出后的恢复。
2. **Memory 长期记忆管理**：负责把对话中值得长期保留的偏好、事实、决策等提炼出来，形成可搜索的长期记忆。

这两者定位不同：

- `context` 保存的是“原始对话记录 + 可恢复的压缩索引”，目标是**不丢历史，可精确召回**。
- `memory` 保存的是“提炼后的长期事实”，目标是**快速注入偏好/画像/稳定决策**。

对我们的项目来说，不建议一开始完整照搬 QwenPaw 的 Scroll 体系。它已经是生产级复杂度，包含 AgentScope 深度 hook、SQLite FTS、召回工具、摘要质量校验、工具结果折叠、sandbox REPL、跨 session 查询等。更合适的路线是先实现一个轻量版：`SessionStore + MessageHistory + ContextBuilder + Summarizer + Recall API`，后续再逐步演进到 Scroll-like 架构。

## 关键源码位置

### 上下文策略接口

- `D:\Project\zsh-project\QwenPaw\src\qwenpaw\agents\context\base.py`

QwenPaw 定义了一个可插拔的 `ContextManager` 协议，核心方法有三个：

- `on_save(agent, blocks)`：每次消息进入 agent 上下文后触发，用于写穿持久化。
- `compress(agent, context_config, instructions)`：上下文超过阈值时执行压缩。
- `recover_from_context_overflow(agent)`：模型服务端返回上下文过长时，尝试强制压缩并重试。

这个接口把“上下文管理策略”从 agent 主逻辑里拆出来。默认可以走 AgentScope 原生压缩，也可以注入 Scroll 策略。

### Scroll 策略入口

- `D:\Project\zsh-project\QwenPaw\src\qwenpaw\agents\context\__init__.py`

`build_scroll_components(...)` 是 Scroll 上下文策略的统一装配入口。它会在 `light_context_config.strategy == "scroll"` 时创建：

- `HistoryStore`：SQLite 历史库。
- `ScrollContextManager`：上下文压缩和索引管理器。
- `recall_history`：结构化召回工具。
- `recall_history_python`：高级 Python REPL 召回工具，默认要求 sandbox。

如果 Scroll 初始化失败，QwenPaw 会降级到 native context 管理，避免 agent 无法启动。

### Agent 接入点

- `D:\Project\zsh-project\QwenPaw\src\qwenpaw\agents\react_agent.py`

`QwenPawAgent` 通过以下方式接入上下文管理：

- 构造函数接收 `context_manager`。
- `_save_to_context(...)` 先调用 AgentScope 原始保存逻辑，再调用 `context_manager.on_save(...)`。
- `_compress_context_impl(...)` 如果存在 `context_manager`，则委托给 `context_manager.compress(...)`。
- `_call_model(...)` 包了一层 overflow recovery：模型报上下文过长时，调用 `context_manager.recover_from_context_overflow(...)`，然后重建 model input 重试一次。
- `_reasoning(...)` 在模型调用成功后，通知 Scroll 哪些 tool result / thinking block 已经被模型看过，后续才允许折叠。

这说明 QwenPaw 的上下文管理不是独立服务，而是深度嵌在 agent 生命周期里。

## ScrollContextManager 的核心设计

主要文件：

- `D:\Project\zsh-project\QwenPaw\src\qwenpaw\agents\context\scroll\manager.py`

`ScrollContextManager` 是 QwenPaw 上下文系统的核心。它做几件事：

1. **写穿持久化**
   - 每次消息进入 live context，就同步写入 `history.db`。
   - 这样即使后续消息被压缩/驱逐，也能从数据库精确恢复。

2. **压力触发压缩**
   - 根据 token 估算和 `trigger_ratio` 判断是否需要压缩。
   - 压缩不是简单删除旧消息，而是尽量保持当前用户请求和最近尾部消息。

3. **保护 active turn**
   - 它会找到最近一个真实 user message，并把它之后的内容作为当前活跃轮次。
   - 即使上下文压力很大，也尽量不把当前任务请求驱逐掉，避免模型回答旧问题。

4. **驱逐中间历史**
   - 旧消息中间段被移出 live context。
   - 被移出的内容写入 eviction index，并保留 seq 范围。

5. **构造上下文占位消息**
   - live context 被重建为：`[压缩索引/摘要 placeholder] + 最近尾部消息`。
   - placeholder 作为一条特殊用户消息进入上下文，里面告诉模型哪些历史被归档，以及如何通过 `recall_history` 找回。

6. **工具结果折叠**
   - 大型 tool result 可以被替换为指针 stub。
   - stub 会告诉模型如何用 `recall_history(op="recall_tool", tool_call_id=...)` 找回完整结果。

7. **溢出恢复**
   - 如果 provider 返回上下文过长，Scroll 会强制压缩一次。
   - 如果还是超限，才抛出 `ContextWindowUnfitError`。

## HistoryStore：原始历史的持久化层

主要文件：

- `D:\Project\zsh-project\QwenPaw\src\qwenpaw\agents\context\scroll\history.py`

`HistoryStore` 使用 SQLite 保存完整对话历史。核心表是 `conversation_history`，主要字段包括：

- `seq`：全局自增序号，也是召回时的精确地址。
- `session_id`：会话 ID。
- `agent_id`：agent ID。
- `kind`：记录类型，例如 `model_turn`、`context_msg`、`tool_result`。
- `role`：user / assistant / system 等角色。
- `name`：工具名或消息名。
- `content`：扁平文本内容。
- `tool_call_id`：工具调用和工具结果之间的关联。
- `tool_input`、`tool_state`：工具输入和状态。
- `headline`：模型输出的检索标题。
- `blocks`：结构化 block 序列，用于恢复原始消息。
- `metadata`：额外元数据。
- `created_at`：创建时间。
- `dedup_key`：幂等去重键。

它还维护 FTS5 全文索引 `conversation_history_fts`，用于搜索历史内容。如果当前 SQLite 不支持 FTS5，则降级为 LIKE 搜索。

值得注意的是，QwenPaw 对 `recall_history` 工具自身产生的日志做了防污染处理：召回工具的查询和输出会写入历史，但不会进入全文索引，避免模型未来搜索时反复搜到自己的搜索记录。

## EvictionIndex：上下文压缩后的地图

主要文件：

- `D:\Project\zsh-project\QwenPaw\src\qwenpaw\agents\context\scroll\eviction_index.py`

`EvictionIndex` 是 Scroll 策略最有特色的部分。它不是把旧历史总结成一句话，而是在 prompt 中放一张“归档地图”。地图里保存：

- 被驱逐历史的 `seq` 范围。
- 关键轮次的 headline。
- 多级 tier 结构。

它的 tier 结构类似里程表：

- Tier 0 保存最近被压缩的块，细节最多。
- 当某个 tier 超过容量，会把旧块折叠成更高 tier 的摘要线。
- 越老的历史越粗略，但每一行仍保留 seq 范围，可以精确召回。

重要原则是：**地图可以有损，但原文不丢**。地图只是帮助模型知道“有什么历史值得 recall”，真正内容仍在 SQLite。

## ContinuationSummary：任务状态摘要

主要文件：

- `D:\Project\zsh-project\QwenPaw\src\qwenpaw\agents\context\scroll\continuation_summary.py`

Scroll 不只保留索引，还会维护一份“当前任务状态摘要”。这份摘要强调：

- 当前任务是什么。
- 当前有效状态是什么。
- 仍然有效的约束是什么。
- 已做出的决策是什么。
- 还有哪些待办或 blocker。

它有严格的 Markdown 结构：

- `Active Task`
- `Current State`
- `Constraints`
- `Decisions`
- `Open Work`

QwenPaw 对摘要做了很多防护：

- 摘要中不能包含 secret。
- 摘要中的 opaque identifier 必须来自证据。
- 摘要不能擅自把“计划/尝试/失败”写成“完成”。
- 摘要的来源 seq 范围由代码管理，不完全信任模型自己生成的引用。

这说明 QwenPaw 把 summary 当作“可用但不完全可信”的模型产物，所以用本地规则校验。

## Recall 工具：让模型主动找回历史

主要文件：

- `D:\Project\zsh-project\QwenPaw\src\qwenpaw\agents\context\scroll\recall_tool.py`
- `D:\Project\zsh-project\QwenPaw\src\qwenpaw\agents\context\scroll\memoryspace.py`
- `D:\Project\zsh-project\QwenPaw\src\qwenpaw\agents\context\scroll\repl.py`

QwenPaw 有两个召回入口。

### `recall_history`

这是推荐路径，是结构化、参数化、只读的工具。支持：

- `op="expand"`：按 seq 范围展开原始历史。
- `op="search"`：关键词搜索历史。
- `op="recall_tool"`：按 `tool_call_id` 找回工具调用和工具结果。
- `op="days_between"`：日期差计算。

因为所有参数都是标量，并且查询使用绑定参数，所以它可以在进程内执行，不需要 sandbox。

### `recall_history_python`

这是高级路径，让模型运行 Python 代码操作 `MemorySpace`。它能力更强，可以做自定义 SQL、scratch table、复杂聚合，但风险也更高，因为它执行模型生成的代码。

QwenPaw 默认要求 sandbox；只有同时满足部署层环境变量和配置开关时，才允许 unsandboxed fallback。

### MemorySpace

`MemorySpace` 为召回工具提供一个 SQLite 工作空间：

- `main` 是模型可读写的 scratch 数据库。
- `hist` 是只读 attach 的 `history.db`。
- SQLite authorizer 禁止对 `hist` 写入、禁止 attach/detach。
- 查询结果有行数、字节数、时间预算，防止一次召回撑爆上下文。

## 系统提示词配合

主要文件：

- `D:\Project\zsh-project\QwenPaw\src\qwenpaw\agents\context\scroll\prompt.py`
- `D:\Project\zsh-project\QwenPaw\src\qwenpaw\runtime\prompt_contributors.py`

QwenPaw 不只是提供工具，还会给模型注入专门的 Scroll 系统提示词。它要求模型：

- 每个有实质任务信息的最终回复都追加一个隐藏 headline。
- 看到 `[context compressed]` 地图时，理解它是历史索引，不是当前用户请求。
- 历史事实不在 live context 时，先调用 `recall_history`，不要猜。
- `memory` 是提炼后的长期记忆，`recall` 才是原始历史真相来源。

这个提示词很关键。没有它，模型可能不知道如何使用 eviction index，也可能把归档 headline 当成当前任务。

## Memory 长期记忆系统

主要文件：

- `D:\Project\zsh-project\QwenPaw\src\qwenpaw\agents\memory\base_memory_manager.py`
- `D:\Project\zsh-project\QwenPaw\src\qwenpaw\agents\memory\reme_light_memory_manager.py`
- `D:\Project\zsh-project\QwenPaw\src\qwenpaw\agents\memory\agent_md_manager.py`

长期记忆系统通过 `BaseMemoryManager` 抽象出来。它的职责包括：

- 提供 `memory_search` 工具。
- 提供 `get_memory_prompt()`，把长期记忆提示注入系统 prompt。
- 提供 `auto_memory(...)`，从消息中提炼记忆。
- 提供 `auto_memory_search(...)`，在回复前自动搜索相关记忆，并把结果作为合成消息插入上下文。
- 支持后台 worker 处理自动记忆任务。
- 支持 backend registry，允许插件注册自己的 memory backend。

QwenPaw 的 memory 与 scroll 的区别很明确：

- Scroll 保存原始历史，用于可验证召回。
- Memory 保存提炼后的长期事实，用于更快更稳定地个性化响应。

## 配置方式

主要文件：

- `D:\Project\zsh-project\QwenPaw\src\qwenpaw\config\config.py`

相关配置包括：

```yaml
running:
  light_context_config:
    strategy: scroll
    token_count_estimate_divisor: 4
    scroll_config:
      db_filename: history.db
      repl_timeout_s: 300
      history_retention_days: 30
      allow_unsandboxed: false
      offload_dialog: false
```

其中：

- `strategy` 默认是 `scroll`。
- `history.db` 位于 workspace 目录下。
- `history_retention_days` 默认 30 天，设为 0 表示永久保留。
- `allow_unsandboxed` 默认 false，而且还要部署层环境变量允许才生效。

## Builder 装配流程

主要文件：

- `D:\Project\zsh-project\QwenPaw\src\qwenpaw\runtime\builder.py`

大致调用链：

1. Builder 先收集普通工具和上下文召回工具。
2. 构建模型，因为 Scroll 需要模型上下文大小做 token 判断。
3. 构建 offloader。
4. 调用 `_build_scroll_components(...)` 创建 Scroll 组件。
5. 判断 recall 能否运行。如果 recall 不能运行，则降级到 native，避免历史被压缩后无法召回。
6. 把 `recall_history` 和可选的 `recall_history_python` 注册进工具集。
7. 构建 toolkit。
8. 创建 `QwenPawAgent`，并把 `context_manager` 注入进去。

这个装配流程有一个非常重要的设计原则：**压缩和召回必须同时可用**。如果能压缩但不能召回，历史就会变成不可恢复的黑洞，所以 QwenPaw 会保守降级。

## 对 private-assistent 的建议

我们当前项目还处在早期阶段，已经有 provider 配置、默认模型和真实模型调用。下一步加上下文管理时，建议分三期做。

### 第一期：轻量会话上下文

目标：让 WebUI/API 支持多轮对话，不再每次只发送单条 message。

建议模块：

```text
src/private_assistent/context/
  __init__.py
  models.py              # ChatMessage, SessionState, ContextConfig
  store.py               # JSONL/SQLite 会话消息存储
  builder.py             # 从 session 历史构建 provider messages
  manager.py             # append / load / clear / build_messages
```

建议能力：

- `session_id` 参数。
- 每轮保存 user 和 assistant 消息。
- 默认读取最近 N 条消息作为上下文。
- 支持 `max_messages`、`max_chars` 或粗略 token 预算。
- `/api/chat` 接收 `session_id`。
- `/api/sessions` 列出会话。
- `/api/sessions/{id}/messages` 查看历史。
- `/api/sessions/{id}` 删除或清空。

这一期不做复杂摘要，不做召回工具，只解决“能连续对话”。

### 第二期：压缩摘要

目标：当历史过长时，保留最近消息，并把旧消息压成一份 summary。

建议新增：

```text
src/private_assistent/context/summarizer.py
src/private_assistent/context/compaction.py
```

建议策略：

- 每个 session 保存 `summary` 字段。
- 构建上下文时使用：`system prompt + summary + recent messages + current user message`。
- 超过阈值时，把旧消息送给当前默认模型生成摘要。
- 摘要结构先保持简单：当前任务、已知事实、用户偏好、未完成事项。

这一期类似 QwenPaw 的 `ContinuationSummary`，但不需要一开始做复杂本地校验。

### 第三期：Scroll-like 原文召回

目标：让被压缩/归档的历史仍能精确召回。

建议新增：

```text
src/private_assistent/context/history.py       # SQLite history store
src/private_assistent/context/search.py        # FTS/LIKE 搜索
src/private_assistent/context/recall.py        # recall API/tool
src/private_assistent/context/eviction_index.py
```

建议能力：

- SQLite 保存完整原始消息。
- 每条消息分配自增 `seq`。
- 压缩时生成一个归档索引，记录 seq 范围和简短标题。
- 给模型提供 `recall_history` 工具，支持 search / expand。
- WebUI 支持搜索历史、查看 session 历史。

这一期才开始接近 QwenPaw 的 Scroll。

## 不建议现在直接复制的部分

QwenPaw 的上下文系统很强，但以下部分不适合当前直接复制：

- AgentScope 深度 hook：我们现在的 agent loop 还没成型，直接复制会产生大量适配成本。
- `recall_history_python`：需要 sandbox 和权限治理，当前项目没必要先做。
- 多 tier eviction index：早期可以先用简单 seq range + summary。
- 工具结果折叠：等工具系统成熟后再做。
- 摘要质量校验：第一版可以先用 prompt 约束，后续再增加 secret redaction 和 identifier 校验。
- Memory backend registry：当前先写内置 SQLite/JSONL 即可，等插件化需求出现再抽象。

## 推荐的第一版数据结构

第一版可以从 SQLite 开始，也可以 JSONL 起步。考虑后续搜索和扩展，建议直接 SQLite。

### `sessions`

```sql
CREATE TABLE sessions (
  id TEXT PRIMARY KEY,
  title TEXT,
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL,
  summary TEXT
);
```

### `messages`

```sql
CREATE TABLE messages (
  id TEXT PRIMARY KEY,
  session_id TEXT NOT NULL,
  seq INTEGER NOT NULL,
  role TEXT NOT NULL,
  content TEXT NOT NULL,
  provider_id TEXT,
  model TEXT,
  metadata TEXT,
  created_at TEXT NOT NULL
);
```

### `context_events`（第二/三期再加）

```sql
CREATE TABLE context_events (
  id TEXT PRIMARY KEY,
  session_id TEXT NOT NULL,
  type TEXT NOT NULL,
  seq_lo INTEGER,
  seq_hi INTEGER,
  summary TEXT,
  metadata TEXT,
  created_at TEXT NOT NULL
);
```

## 推荐实施顺序

1. 先实现 session/message 持久化。
2. 修改 provider adapter，使它支持传入 `messages`，而不是只有单条 `message`。
3. 修改 `/api/chat`：接收 `session_id`，读取历史，构建上下文，调用模型，保存回复。
4. WebUI 增加会话列表和当前会话历史展示。
5. 加入上下文窗口限制：先保留最近 N 条。
6. 加入摘要压缩。
7. 最后再做原文召回和搜索。

## 对当前项目的架构判断

`private-assistent` 当前还没到 QwenPaw 的复杂度，所以应该先保留清晰边界：

```text
API 层
  只负责请求/响应、session_id、WebUI 数据接口

Assistant/Agent 层
  负责组织一次对话调用

Context 层
  负责历史读取、写入、裁剪、摘要、召回

Provider 层
  负责把 messages 转换成不同 provider 协议并调用模型
```

这样未来无论接 AgentScope、AutoGen、LangGraph，还是自研 agent loop，上下文层都能复用。

## 最小可落地方案

下一步最小改动建议：

1. 新建 `private_assistent.context` 包。
2. 加 `SQLiteSessionStore`。
3. 把 `ProviderManager.generate(message)` 扩展为 `generate_messages(messages)`。
4. `/api/chat` 请求体增加 `session_id`，默认 `default`。
5. 每次请求流程变为：
   - 保存 user message。
   - 读取当前 session 最近消息。
   - 调用模型。
   - 保存 assistant reply。
   - 返回 reply 和 session_id。
6. WebUI 先只展示当前 session 的多轮消息。

这一步完成后，我们就有了真正的多轮上下文基础，再考虑摘要和召回。
