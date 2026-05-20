# Qwen2api Agent Guide

适用范围：本文件位于仓库根目录，约束整个 `F:\git\Qwen2api` 项目及其所有子目录。

## 工作原则

- 先调查再改代码。任何业务修改前，先从入口、调用链、配置、持久化数据和运行日志确认真实归因。
- 静态阅读无法证明的问题，必须写临时脚本、HTTP 调用或浏览器自动化进行动态验证。
- 修复时做横向扫描：同类协议转换、鉴权、账号池状态、模型解析、图片缓存、运行时配置等逻辑要统一处理。
- 优先保持现有架构和模块边界，不做局部补丁式绕过。逻辑已经腐烂时，应重写成线性、可解释的实现。
- 不提交或泄漏 `data/`、`logs/`、账号 token、邮箱密钥、API key 等运行态敏感信息。

## 项目功能概要

Qwen2api 是一个 FastAPI 网关，把 `https://chat.qwen.ai` 的 Qwen 网页能力包装成兼容 API，供 Cherry Studio、Cursor、Claude Code、Cline、New-API 等客户端调用。

当前代码实际注册的能力：

- OpenAI Chat Completions：`/v1/chat/completions`、`/chat/completions`、`/completions`
- OpenAI Responses API：`/v1/responses`
- Anthropic Messages：`/anthropic/v1/messages`、`/v1/messages`
- Images：`/v1/images/generations`、`/images/generations`、`/v1/images/edits`、`/images/edits`
- Models / health：`/v1/models`、`/models`、`/health`、`/healthz`
- 管理后台 API：`/api/admin/*`
- 静态管理页：`/admin/login`、`/admin/accounts`、`/admin/config`、`/admin/register`、`/admin/cache`
- 内置 WebUI：`/webui/login`、`/webui/chat`
- 本地图片代理：`/v1/files/image?id=...`、`/proxy/image/{image_id}`

当前实现边界：

- `backend/api/embeddings.py` 只是 501 stub，未实现 embeddings。
- README 声明了 Gemini `generateContent` 端点，但当前磁盘代码没有 `backend/api/gemini.py`，`backend/main.py` 也未注册 Gemini 路由。涉及 Gemini 时先补证或补实现。
- `backend/core/browser_engine.py` 当前是 stub，内部委托 `HttpxEngine`，不是实际 Camoufox 浏览器会话。Dockerfile 仍安装 Camoufox 和 Playwright，用于依赖兼容和注册链路。

## 技术栈

- 语言与运行时：Python，`.python-version` 为 `3.13`；Docker 使用 `python:3.12-slim`；`start.py` 的最低检查是 Python 3.10+。
- Web 框架：FastAPI + Uvicorn。
- 配置：`pydantic-settings`，`.env`，环境变量，`data/runtime_settings.json` 运行时持久化。
- 上游访问：`curl_cffi` Chrome TLS 指纹直连、`httpx`、Camoufox/Playwright 相关依赖。
- 持久化：本地 JSON 文件，无外部数据库。主要在 `data/` 下保存账号、密钥、运行时设置、使用统计、健康快照和图片缓存。
- 前端：`statics/` 下纯 HTML/CSS/JS 管理面板和 WebUI。
- 容器：`Dockerfile`、`docker-compose.yml`，默认端口 `7860`，健康检查走 `/healthz`。

## 架构总览

```text
client
  -> FastAPI route in backend/api/*
  -> backend.core.auth / admin auth
  -> protocol adapter and prompt conversion
  -> backend.engine.completion
  -> backend.services.qwen_client
  -> backend.core.account_pool acquire/release account
  -> gateway engine: HttpxEngine / BrowserEngine stub / HybridEngine
  -> chat.qwen.ai upstream
  -> SSE or JSON response adapter
  -> usage, health, logs, image cache persistence
```

启动入口是 `backend/main.py`：

- `lifespan()` 创建 `AsyncJsonDB`、`BrowserEngine`、`HttpxEngine`、`HybridEngine`、`AccountPool`、`QwenClient`。
- 根据 `settings.ENGINE_MODE` 选择 `httpx`、`browser` 或 `hybrid`。
- 加载账号池，启动账号池后台任务、使用统计、健康快照、会话垃圾回收、自动补号循环。
- 注册所有 API 路由、静态页面、WebUI 页面和图片代理路由。

`start.py` 是本地启动脚本，会创建 `data/` 与 `logs/`，安装 `backend/requirements.txt`，杀掉目标端口已有进程，再用单 worker 启动 `backend.main:app`。

## 目录规划

```text
backend/
  main.py                  FastAPI 应用入口、生命周期、路由和静态页挂载
  api/                     对外协议层，只做鉴权、格式转换、调用核心引擎、格式化响应
    admin/                 管理后台 API 聚合和子模块
  core/                    配置、鉴权、账号池、引擎、持久化、统计、健康快照等基础设施
  engine/                  协议无关的 completion 执行器
  services/                Qwen 上游客户端、prompt/tool 处理、注册、邮箱、文件、图片代理等服务
statics/                   管理后台和 WebUI 静态资源
data/                      本地运行态数据，禁止提交敏感内容
logs/                      运行日志，禁止提交
Dockerfile                 容器镜像构建
docker-compose.yml         Compose 部署入口
start.py                   本地一键启动入口
```

放置新代码时遵循：

- 新协议端点放 `backend/api/`，不要把业务重逻辑塞进路由文件。
- 账号调度、熔断、限流、补号状态归 `backend/core/account_pool.py`。
- 上游 Qwen 会话、SSE 解析、换号重试归 `backend/services/qwen_client.py`。
- OpenAI/Anthropic/Responses 共用的补全执行逻辑归 `backend/engine/completion.py`。
- 邮箱渠道适配归 `backend/services/mail_service.py`，注册编排归 `backend/services/register.py` 或 `browser_register.py`。
- 静态管理页只放 `statics/`，对应管理 API 放 `backend/api/admin/`。

## 核心模块与文件

- `backend/main.py`：应用总入口；生命周期初始化；路由注册；静态管理页、WebUI、图片代理。
- `backend/core/config.py`：`Settings`、数据路径、运行时设置持久化、API key 文件、内置模型、`resolve_model()`、`resolve_model_thinking()`、安全配置校验。
- `backend/core/auth.py`：统一 API key 提取与验证，支持 Bearer、`x-api-key`、`key`、`api_key`。
- `backend/core/database.py`：`AsyncJsonDB`，异步锁保护的 JSON 文件存储。
- `backend/core/account_pool.py`：`Account` 与 `AccountPool`；账号状态、Min-Heap/score 调度、粘性会话、JWT 过期过滤、RPM/TPM、断路器、SSE 事件、自动补号。
- `backend/core/httpx_engine.py`：`curl_cffi` 直连 Qwen API，包含普通 API 调用和 SSE 流读取。
- `backend/core/browser_engine.py`：当前为同接口 stub，委托 `HttpxEngine`。
- `backend/core/hybrid_engine.py`：组合引擎；`api_call` 优先 httpx，失败回退 browser stub；`fetch_chat` 走 httpx。
- `backend/core/usage.py`：请求 token 和耗时统计，持久化到 `data/usage_stats.json`。
- `backend/core/health_snapshot.py`：每 30 秒记录账号池健康历史到 `data/health_history.json`。
- `backend/engine/completion.py`：统一 completion 执行器；处理流式/非流式、工具调用、XML fallback、Native tool chunk、reasoning、usage。
- `backend/api/chat.py`：OpenAI Chat Completions 路由；媒体意图检测；`qwen-image` 和 T2I 分流。
- `backend/api/responses.py`：OpenAI Responses API 适配层。
- `backend/api/anthropic.py`：Anthropic Messages 适配层。
- `backend/api/images.py`：OpenAI Images generation/edit 兼容接口。
- `backend/api/probes.py`：健康检查与模型列表。
- `backend/api/embeddings.py`：未实现 stub。
- `backend/api/admin/*.py`：账号、密钥、设置、状态、日志、用量、图片缓存管理。
- `backend/services/qwen_client.py`：Qwen 会话创建/删除、token 校验、payload 构建、SSE 解析、聊天和图片生成换号重试。
- `backend/services/prompt_builder.py`：OpenAI messages/tools 到 Qwen prompt 的转换，包含工具示例和 tool_choice 指令。
- `backend/services/tool_parser.py`：工具调用 JSON 修复、解析、代码块过滤、Native chunk 组装、防泄漏状态。
- `backend/services/register.py`：批量注册编排，调用邮箱渠道和账号池写入。
- `backend/services/browser_register.py`：Playwright 注册流程。
- `backend/services/mail_service.py`：MoeMail、TempMail、GuerrillaMail、GPTMail、VipMail 等邮箱渠道。
- `backend/services/file_uploader.py`：多模态文件提取、STS 获取、OSS 上传、解析等待。
- `backend/services/image_proxy.py`：下载并缓存图片到 `data/files/images/`，提供容量管理和代理 URL。
- `backend/services/garbage_collector.py`：清理不活跃 Qwen chat。
- `backend/services/log_manager.py`：内存日志捕获，供管理后台查询。

## 主要功能链路

### 启动链路

1. `start.py` 或 Uvicorn 启动 `backend.main:app`。
2. `lifespan()` 初始化 JSON 存储、网关引擎、账号池、QwenClient。
3. `AccountPool.load()` 从 `settings.ACCOUNTS_FILE` 加载账号，启动断路器恢复、粘性映射清理、token 过期清理等后台任务。
4. `UsageManager`、`HealthSnapshotManager`、`garbage_collect_chats()` 和自动补号循环开始运行。

### Chat Completions 链路

1. `backend/api/chat.py` 接收请求并调用 `verify_api_key()`。
2. `resolve_model()` 和 `resolve_model_thinking()` 解析模型名、thinking/nothinking 后缀和 Qwen 3.7 映射。
3. `messages_to_prompt()` 将 OpenAI messages 和 tools 转成 Qwen prompt。
4. 普通文本进入 `backend.engine.completion.completions()`；图片意图或 `qwen-image` 进入 `_handle_t2i()`。
5. `completion.py` 根据 stream/tools 分流到 `_stream_no_tools()`、`_stream_with_tools()` 或 `_batch()`。
6. `QwenClient.chat_stream_events_with_retry()` 从账号池取账号，创建 Qwen chat，构建 payload，读取上游 SSE。
7. 失败时按错误类型标记账号：rate limit、auth、banned、transient、circuit；必要时换号重试。
8. 响应按 OpenAI SSE 或 JSON 格式返回，并写入 usage 统计。

### Responses 与 Anthropic 链路

- `backend/api/responses.py` 和 `backend/api/anthropic.py` 是协议适配层。
- 两者先把各自协议的 input/messages/tools 转成 OpenAI-like messages，然后调用 `completions_raw()`。
- 输出再转换回 Responses API 或 Anthropic Messages 的响应格式。

### 工具调用链路

1. `prompt_builder.py` 注入工具格式说明、示例、tool_choice 约束和读工具防循环提示。
2. `completion.py` 优先处理 Qwen Native tool chunks；如果 Native 工具被上游阻断或输出异常，切 XML fallback。
3. `tool_parser.py` 负责解析、修复 JSON、过滤代码块内伪工具调用、构建 OpenAI tool call blocks。
4. 涉及工具调用质量问题时，不要只改一个协议路由，应同时检查 `prompt_builder.py`、`completion.py`、`tool_parser.py`。

### 图片链路

1. `/v1/images/generations` 或 Chat 中 T2I 意图进入 `backend/api/images.py` / `chat.py`。
2. `QwenClient.image_generate_with_retry()` 走账号池和上游 Qwen 图片模式。
3. `image_proxy.py` 可把上游图片下载到 `data/files/images/`，按 `IMAGE_FORMAT` 返回 qwen URL、本地 URL、Markdown 或 base64。
4. 管理后台缓存 API 使用同一 `image_proxy.py` 查询、删除、清空本地图片。

### 管理后台链路

1. 静态页面在 `statics/`，页面路径由 `backend/main.py` 直接返回 `FileResponse`。
2. 管理 API 在 `/api/admin/*`，统一由 `backend/api/admin/__init__.py` 的 `_require_admin()` 鉴权。
3. 账号管理读写 `request.app.state.account_pool` 和 `accounts_db`。
4. 设置管理修改 `settings` 后调用 `save_runtime_settings()` 落盘到 `data/runtime_settings.json`。
5. 密钥管理读写 `data/api_keys.json`。
6. 状态、日志、用量和健康历史来自 `AccountPool`、`log_manager`、`UsageManager`、`HealthSnapshotManager`。

### 自动注册与补号链路

1. 管理 API 或账号池自动补号循环调用 `perform_batch_registration()`。
2. `register.py` 根据 provider 选择邮箱渠道，创建邮箱，完成 Qwen 注册/激活，拿到 token。
3. 成功账号通过 `AccountPool.add_account()` 写入池并持久化。
4. 邮箱渠道包括 MoeMail、TempMail、GuerrillaMail、GPTMail、VipMail；改动某个渠道时要横向检查公共激活链接解析、轮询超时、代理配置和错误分类。

## 数据与配置

主要配置在 `.env.example`、环境变量和 `backend/core/config.py`：

- 服务：`ADMIN_KEY`、`PORT`、`APP_URL`、`DEFAULT_STREAM`
- 引擎：`ENGINE_MODE=httpx|browser|hybrid`、`BROWSER_POOL_SIZE`
- 账号池：`MAX_RPM_PER_ACCOUNT`、`MAX_TPM_PER_ACCOUNT`、`MAX_INFLIGHT_PER_ACCOUNT`、`CIRCUIT_BREAKER_THRESHOLD`
- 补号：`AUTO_REPLENISH`、`REPLENISH_TARGET`、`REPLENISH_CONCURRENCY`、`REPLENISH_PROVIDER`
- 邮箱：`MOEMAIL_*`、`TEMPMAIL_*`、`SMARTMAIL_KEY`、`VIPMAIL_KEY`
- 代理：`PROXY_ENABLED`、`PROXY_URL`、`PROXY_USERNAME`、`PROXY_PASSWORD`
- 图片：`IMAGE_FORMAT`、`IMAGE_CACHE_MAX_MB`
- WebUI：`WEBUI_ENABLED`、`WEBUI_KEY`
- 超时与流：`TIMEOUT_*`、`STREAM_KEEPALIVE_INTERVAL`、`STREAM_MAX_CHUNK_SIZE`、`STREAM_CHUNK_DELAY_MS`

主要运行态文件：

- `data/accounts.json`：账号池，含 token，敏感。
- `data/api_keys.json`：API key 集合，敏感。
- `data/runtime_settings.json`：管理后台保存的运行时配置。
- `data/usage_stats.json`：调用统计。
- `data/health_history.json`：账号池健康快照。
- `data/files/images/`：本地图片缓存。
- `logs/`：容器或本地运行日志。

## 模型与 thinking 规则

- 内置模型列表在 `backend/core/config.py` 的 `BUILTIN_MODELS`。
- 默认模型是 `qwen3.6-plus`。
- `-thinking` 后缀强制 thinking，`-nothinking` 后缀关闭 thinking，无后缀交给 Qwen 自动判断。
- Qwen 3.7 preview 会映射到 invite beta 内部 ID，并始终 thinking。
- `DEFAULT_MODEL_ALIASES` 当前为空，默认别名映射已禁用；`MODEL_MAP` 仅由运行时配置提供。

## 开发与验证

常用启动：

```powershell
pip install -r backend/requirements.txt
python start.py
```

或直接启动：

```powershell
$env:PYTHONPATH = (Get-Location).Path
python -m uvicorn backend.main:app --host 0.0.0.0 --port 7860 --workers 1
```

Docker：

```powershell
docker compose up -d
```

基础验证：

```powershell
python -m compileall backend start.py
curl http://127.0.0.1:7860/healthz
curl http://127.0.0.1:7860/v1/models
```

当前仓库未发现正式 `tests/` 目录。新增业务逻辑时，如果已有测试不足，应把调查阶段的脚本沉淀成可重复测试或至少保留清晰的验证命令与输入输出证据。

## 修改注意事项

- 改协议适配时，检查 Chat、Responses、Anthropic 三条链路是否共享同一问题。
- 改鉴权时，统一检查 `backend/core/auth.py` 和 `backend/api/admin/__init__.py`，二者面向不同调用面。
- 改模型解析时，同时检查 `/v1/models`、`resolve_model()`、`resolve_model_thinking()`、README 和管理后台展示。
- 改账号池状态时，同时检查 admin 状态页、SSE events、health snapshot、自动补号触发、QwenClient 错误分类。
- 改图片链路时，同时检查 Chat T2I、Images API、`image_proxy.py`、缓存管理页和 `APP_URL` 行为。
- 改注册链路时，必须区分邮箱渠道错误、代理错误、浏览器自动化错误、Qwen 激活/token 错误。
- 改前端静态页时，使用浏览器验证 DOM、网络请求和移动/桌面布局，不要只看 HTML。
- 若文档和代码冲突，以当前磁盘代码和动态验证为准，并同步更新文档。
