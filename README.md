<p align="center">
  <img src="logo.svg" width="120" alt="Qwen2api"/>
</p>

<h1 align="center">Qwen2api</h1>

<p align="center">
  <a href="https://github.com/jiujiu532/Qwen2api/actions/workflows/docker-publish.yml">
    <img src="https://github.com/jiujiu532/Qwen2api/actions/workflows/docker-publish.yml/badge.svg" alt="Build"/>
  </a>
  <img src="https://img.shields.io/badge/python-3.12+-blue?logo=python" alt="Python"/>
  <img src="https://img.shields.io/badge/docker-ghcr.io%2Fjiujiu532%2Fqwen2api-blue?logo=docker" alt="Docker"/>
  <img src="https://img.shields.io/badge/license-MIT-green" alt="License"/>
</p>

<p align="center">
  Qwen AI 逆向网关 -- 标准 OpenAI / Anthropic / Gemini API 兼容
</p>

<p align="center">中文 | <a href="README.en.md">English</a></p>

---

## 概述

Qwen2api 将阿里通义千问（Qwen）网页版的能力以标准 API 格式对外暴露。多账号池轮询、自动注册补号、工具调用、流式输出，可直接对接 Cherry Studio、Cursor、Claude Code、Cline、New-API 等客户端。

## 核心特性

- **多协议兼容** -- OpenAI Chat Completions / Responses API / Anthropic Messages / Gemini generateContent 四协议同时支持
- **账号池调度** -- Min-Heap 优先级调度，6 态生命周期管理，断路器自动熔断
- **自动注册补号** -- 支持 MoeMail / TempMail / GuerrillaMail / GPTMail / YYDS 五渠道
- **工具调用** -- Native FC 优先 + XML Fallback 双模式，流式防泄漏状态机，循环检测
- **思考模式** -- 模型名后缀控制（-thinking / -nothinking），或 reasoning_effort 参数覆盖
- **图片生成** -- 兼容 OpenAI DALL-E 接口，自动检测用户意图路由到 T2I
- **精确 Token 统计** -- 直接从 Qwen 上游 SSE 提取真实 usage，非本地估算
- **管理面板** -- 纯 HTML 管理 UI，账号/密钥/设置/缓存/注册一站式管理
- **WebUI** -- 内置 Web 聊天界面，支持多会话、思考过程显示
- **多引擎** -- httpx 直连（快）/ Camoufox 浏览器指纹（防封）/ hybrid 混合
- **容灾重试** -- 上游失败自动换号，NativeBlock 检测自动切 XML 模式

## 支持的端点

| 协议 | 端点 | 功能 |
|------|------|------|
| OpenAI | `POST /v1/chat/completions` | 聊天补全（流式/非流式/工具调用/思考模式） |
| OpenAI | `POST /v1/responses` | Responses API（Codex / Agents） |
| OpenAI | `POST /v1/images/generations` | 图片生成 |
| OpenAI | `POST /v1/embeddings` | 文本嵌入 |
| OpenAI | `GET /v1/models` | 模型列表 |
| Anthropic | `POST /v1/messages` | Claude 兼容（含 tool_use / thinking） |
| Gemini | `POST /v1beta/models/{m}:generateContent` | Gemini 兼容 |
| Gemini | `POST /v1beta/models/{m}:streamGenerateContent` | Gemini 流式 |

## 可用模型

| 模型名 | 说明 |
|--------|------|
| `qwen3.6-plus` | 主力模型，自动思考 |
| `qwen3.6-plus-thinking` | 强制深度思考 |
| `qwen3.6-plus-nothinking` | 快速模式，关闭思考 |
| `qwen3.6-max-preview` | 高性能预览版 |
| `qwen3.6-27b` | 轻量版 |
| `qwen3.6-27b-nothinking` | 轻量快速模式 |
| `qwen3.7-max-preview-thinking` | 3.7 Max 预览（强制思考） |
| `qwen3.7-plus-preview-thinking` | 3.7 Plus 预览（强制思考） |
| `qwen-image` | 图片生成专用 |

所有模型均为 Qwen 真实内置模型，无别名映射。

## 快速开始

### Docker（推荐）

```bash
docker run -d \
  --name qwen2api \
  -p 7860:7860 \
  -e ADMIN_KEY=your-admin-key \
  -v ./data:/workspace/data \
  ghcr.io/jiujiu532/qwen2api:latest
```

docker-compose:

```bash
cp .env.example .env
# 编辑 .env 设置 ADMIN_KEY 和邮箱渠道
docker-compose up -d
```

### 本地运行

```bash
# Python 3.12+
pip install -r backend/requirements.txt
playwright install chromium  # 注册功能需要
python start.py
```

启动后访问 `http://localhost:7860`，默认管理密钥 `123456`。

## 配置

通过 `.env` 或环境变量：

| 变量 | 默认值 | 说明 |
|------|--------|------|
| `ADMIN_KEY` | `123456` | 管理面板密钥 |
| `PORT` | `7860` | 服务端口 |
| `ENGINE_MODE` | `httpx` | httpx / browser / hybrid |
| `AUTO_REPLENISH` | `false` | 自动补号开关 |
| `REPLENISH_TARGET` | `30` | 目标账号数 |
| `REPLENISH_PROVIDER` | - | 补号邮箱渠道 |
| `MOEMAIL_DOMAIN` | - | MoeMail 域名 |
| `MOEMAIL_KEY` | - | MoeMail 密钥 |
| `TEMPMAIL_DOMAIN` | - | TempMail 域名 |
| `TEMPMAIL_KEY` | - | TempMail 密钥 |
| `SMARTMAIL_KEY` | - | GPTMail 密钥（留空用公共密钥） |
| `VIPMAIL_KEY` | - | YYDS (215.im) 密钥 |
| `PROXY_URL` | - | 注册代理地址 |
| `PROXY_ENABLED` | `false` | 启用出站代理 |
| `IMAGE_FORMAT` | `local_md` | 图片返回格式 |
| `DEFAULT_STREAM` | `true` | 默认流式输出 |

完整配置见 [.env.example](.env.example)。

## 使用示例

### OpenAI 格式

```bash
curl http://localhost:7860/v1/chat/completions \
  -H "Authorization: Bearer your-api-key" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "qwen3.6-plus",
    "messages": [{"role": "user", "content": "Hello"}],
    "stream": true
  }'
```

### 工具调用

```bash
curl http://localhost:7860/v1/chat/completions \
  -H "Authorization: Bearer your-api-key" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "qwen3.6-plus-nothinking",
    "messages": [{"role": "user", "content": "北京天气"}],
    "tools": [{"type": "function", "function": {"name": "get_weather", "parameters": {"type": "object", "properties": {"city": {"type": "string"}}}}}]
  }'
```

### 图片生成

```bash
curl http://localhost:7860/v1/images/generations \
  -H "Authorization: Bearer your-api-key" \
  -H "Content-Type: application/json" \
  -d '{"model": "qwen-image", "prompt": "一只可爱的猫咪", "size": "1024x1024"}'
```

## 管理面板

| 页面 | 路径 | 功能 |
|------|------|------|
| 账号管理 | `/admin/accounts` | 添加/删除/验证/禁用，批量导入导出，关闭记忆 |
| 系统设置 | `/admin/config` | 引擎/邮箱/代理/密钥/超时/图片格式 |
| 扩容中心 | `/admin/register` | 批量注册，多邮箱渠道，SSE 实时进度 |
| 缓存管理 | `/admin/cache` | 图片缓存统计与清理 |
| WebUI | `/webui/chat` | 内置聊天界面 |

## 客户端对接

| 客户端 | 配置方式 |
|--------|----------|
| Cherry Studio | API Base: `http://host:7860/v1`，模型选 `qwen3.6-plus` |
| Cursor | Settings > Models > OpenAI API Base |
| Claude Code | `ANTHROPIC_BASE_URL=http://host:7860` |
| Cline | OpenAI Compatible，填入 Base URL |
| New-API | 添加渠道，类型 OpenAI，代理地址填本服务 |

## License

MIT
