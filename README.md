<p align="center">
  <img src="logo.svg" width="120" alt="qwen2api"/>
</p>

<h1 align="center">qwen2api</h1>

<p align="center">
  <a href="https://github.com/jiujiu532/Qwen2api/actions/workflows/docker-publish.yml">
    <img src="https://github.com/jiujiu532/Qwen2api/actions/workflows/docker-publish.yml/badge.svg" alt="Build"/>
  </a>
  <img src="https://img.shields.io/badge/python-3.12+-blue?logo=python" alt="Python"/>
  <img src="https://img.shields.io/badge/docker-ghcr.io%2Fjiujiu532%2Fqwen2api-blue?logo=docker" alt="Docker"/>
  <img src="https://img.shields.io/badge/license-MIT-green" alt="License"/>
</p>

<p align="center">
  将 Qwen AI 转换为标准 OpenAI / Anthropic / Gemini 兼容 API 的企业级网关
</p>

<p align="center">中文 | <a href="README.en.md">English</a></p>

---

## 什么是 qwen2api

qwen2api 是一个高性能 API 网关，将阿里通义千问（Qwen）的能力以标准 API 格式对外暴露。支持多账号池管理、自动注册补号、工具调用、流式输出，可直接对接 Cherry Studio、Cursor、Claude Code、New-API 等客户端。

## 核心特性

| 特性 | 说明 |
|------|------|
| **多协议兼容** | 同时支持 OpenAI / Anthropic / Gemini / Responses API |
| **账号池调度** | Min-Heap 调度、6 态生命周期、断路器、自适应限流 |
| **自动注册** | 支持 MoeMail / TempMail / GuerrillaMail 自动注册 Qwen 账号 |
| **自动补号** | 账号耗尽时自动触发应急注册，保持服务可用 |
| **工具调用** | XML 格式解析 + 防泄漏状态机 + 循环检测 |
| **思考模式** | 支持自动/思考/快速三种模式，通过模型名后缀切换 |
| **图片生成** | 兼容 OpenAI DALL-E 接口，底层调用 Qwen 图片生成 |
| **管理面板** | 内置 Web 管理后台，实时监控、账号管理、设置配置 |
| **多引擎** | httpx 直连 / Camoufox 浏览器指纹 / 混合模式 |
| **过期清理** | 自动检测并清理过期 JWT token |

## 支持的 API 端点

| 协议 | 端点 | 说明 |
|------|------|------|
| OpenAI | `POST /v1/chat/completions` | 聊天补全（流式/非流式） |
| OpenAI | `POST /v1/responses` | Responses API（Codex/Agents） |
| OpenAI | `POST /v1/images/generations` | 图片生成 |
| OpenAI | `GET /v1/models` | 模型列表 |
| Anthropic | `POST /v1/messages` | Claude 兼容（含 tool_use） |
| Gemini | `POST /v1beta/models/{model}:generateContent` | Gemini 兼容 |
| Gemini | `POST /v1beta/models/{model}:streamGenerateContent` | Gemini 流式 |
| 系统 | `GET /healthz` | 健康检查 |

## 内置模型

| 模型名 | 说明 |
|--------|------|
| `qwen3.6-plus` | 主力模型（自动思考模式） |
| `qwen3.6-plus-thinking` | 强制深度思考 |
| `qwen3.6-plus-nothinking` | 快速模式，跳过思考 |
| `qwen3.6-max-preview` | 高性能预览版 |
| `qwen3.6-max-preview-thinking` | 高性能 + 深度思考 |
| `qwen3.6-max-preview-nothinking` | 高性能 + 快速模式 |
| `qwen3.6-27b` | 轻量版 |
| `qwen3.6-27b-thinking` | 轻量 + 深度思考 |
| `qwen3.6-27b-nothinking` | 轻量 + 快速模式 |

同时内置 39 个常见模型别名映射（gpt-4o、claude-3-5-sonnet、gemini-2.5-pro 等），无需配置即可使用。

## 快速开始

### Docker 部署（推荐）

```bash
# 拉取镜像
docker pull ghcr.io/jiujiu532/qwen2api:latest

# 启动
docker run -d \
  -p 7860:7860 \
  -e ADMIN_KEY=your-admin-key \
  -v ./data:/workspace/data \
  ghcr.io/jiujiu532/qwen2api:latest
```

或使用 docker-compose：

```bash
cp .env.example .env
# 编辑 .env 设置 ADMIN_KEY
docker-compose up -d
```

### 本地运行

```bash
# 需要 Python 3.12+
python start.py
```

启动后访问 `http://localhost:7860` 进入管理面板，默认密码 `123456`。

## 配置说明

通过 `.env` 文件或环境变量配置：

| 变量 | 默认值 | 说明 |
|------|--------|------|
| `ADMIN_KEY` | `123456` | 管理面板登录密钥 |
| `PORT` | `7860` | 服务端口 |
| `ENGINE_MODE` | `hybrid` | 引擎模式：httpx / browser / hybrid |
| `AUTO_REPLENISH` | `false` | 是否开启自动补号 |
| `REPLENISH_TARGET` | `30` | 目标账号数量 |
| `MOEMAIL_DOMAIN` | — | MoeMail 域名（自动注册用） |
| `MOEMAIL_KEY` | — | MoeMail API 密钥 |
| `PROXY_URL` | — | 代理地址（注册用） |

完整配置见 `.env.example`。

## 使用方式

### OpenAI 兼容

```bash
curl http://localhost:7860/v1/chat/completions \
  -H "Authorization: Bearer your-api-key" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "qwen3.6-plus-nothinking",
    "messages": [{"role": "user", "content": "你好"}],
    "stream": true
  }'
```

### Anthropic 兼容

```bash
curl http://localhost:7860/v1/messages \
  -H "x-api-key: your-api-key" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "claude-3-5-sonnet-latest",
    "messages": [{"role": "user", "content": "你好"}],
    "max_tokens": 1024
  }'
```

### 图片生成

```bash
curl http://localhost:7860/v1/images/generations \
  -H "Authorization: Bearer your-api-key" \
  -H "Content-Type: application/json" \
  -d '{"prompt": "一只赛博朋克风格的猫", "n": 1, "size": "1024x1024"}'
```

## 管理面板

访问 `http://localhost:7860` 进入管理面板：

- **监控总览**：请求次数、Token 消耗、RPM/TPM、健康度
- **账号管理**：添加/删除/验证账号，批量导入，JSON 编辑
- **扩容中心**：批量注册新账号，支持多种邮箱渠道
- **系统设置**：模型映射、引擎模式、代理配置、自动补号
- **API 密钥**：生成和管理下游 API Key

## 项目结构

```
qwen2api/
├── backend/
│   ├── api/          # API 端点（chat/anthropic/gemini/responses/images）
│   ├── core/         # 核心模块（账号池/配置/引擎/数据库）
│   └── services/     # 业务服务（注册/Qwen客户端/工具解析）
├── frontend/         # React 管理面板
├── data/             # 运行时数据（账号/配置/统计）
├── docker-compose.yml
├── Dockerfile
└── start.py          # 一键启动脚本
```

## License

MIT
