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
  Enterprise gateway that exposes Qwen AI as standard OpenAI / Anthropic / Gemini compatible APIs
</p>

<p align="center"><a href="README.md">中文</a> | English</p>

---

## What is qwen2api

qwen2api is a high-performance API gateway that converts Alibaba's Qwen AI into standard API formats. It features multi-account pool management, automatic registration, tool calling support, and streaming output. Compatible with Cherry Studio, Cursor, Claude Code, New-API, and other clients.

## Key Features

| Feature | Description |
|---------|-------------|
| **Multi-Protocol** | OpenAI / Anthropic / Gemini / Responses API simultaneously |
| **Account Pool** | Min-Heap scheduling, 6-state lifecycle, circuit breaker, adaptive rate limiting |
| **Auto-Registration** | MoeMail / TempMail / GuerrillaMail automated Qwen account signup |
| **Auto-Replenishment** | Emergency registration when accounts are exhausted |
| **Tool Calling** | XML format parsing + anti-leak state machine + loop detection |
| **Thinking Modes** | Auto / Thinking / Fast modes via model name suffix |
| **Image Generation** | OpenAI DALL-E compatible endpoint powered by Qwen |
| **Admin Dashboard** | Built-in web UI for monitoring, account management, and configuration |
| **Multi-Engine** | httpx direct / Camoufox browser fingerprint / hybrid mode |
| **Token Cleanup** | Automatic detection and removal of expired JWT tokens |

## Supported API Endpoints

| Protocol | Endpoint | Description |
|----------|----------|-------------|
| OpenAI | `POST /v1/chat/completions` | Chat completions (streaming/non-streaming) |
| OpenAI | `POST /v1/responses` | Responses API (Codex/Agents) |
| OpenAI | `POST /v1/images/generations` | Image generation |
| OpenAI | `GET /v1/models` | Model list |
| Anthropic | `POST /v1/messages` | Claude compatible (with tool_use) |
| Gemini | `POST /v1beta/models/{model}:generateContent` | Gemini compatible |
| Gemini | `POST /v1beta/models/{model}:streamGenerateContent` | Gemini streaming |
| System | `GET /healthz` | Health check |

## Built-in Models

| Model | Description |
|-------|-------------|
| `qwen3.6-plus` | Primary model (auto thinking mode) |
| `qwen3.6-plus-thinking` | Forced deep thinking |
| `qwen3.6-plus-nothinking` | Fast mode, skip thinking |
| `qwen3.6-max-preview` | High-performance preview |
| `qwen3.6-max-preview-thinking` | High-performance + deep thinking |
| `qwen3.6-max-preview-nothinking` | High-performance + fast mode |
| `qwen3.6-27b` | Lightweight |
| `qwen3.6-27b-thinking` | Lightweight + deep thinking |
| `qwen3.6-27b-nothinking` | Lightweight + fast mode |

Also includes 39 built-in model aliases (gpt-4o, claude-3-5-sonnet, gemini-2.5-pro, etc.) that work out of the box.

## Quick Start

### Docker (Recommended)

```bash
docker pull ghcr.io/jiujiu532/qwen2api:latest

docker run -d \
  -p 7860:7860 \
  -e ADMIN_KEY=your-admin-key \
  -v ./data:/workspace/data \
  ghcr.io/jiujiu532/qwen2api:latest
```

Or with docker-compose:

```bash
cp .env.example .env
# Edit .env to set ADMIN_KEY
docker-compose up -d
```

### Local Development

```bash
# Requires Python 3.12+
python start.py
```

Access `http://localhost:7860` for the admin dashboard. Default password: `123456`.

## Configuration

Configure via `.env` file or environment variables:

| Variable | Default | Description |
|----------|---------|-------------|
| `ADMIN_KEY` | `123456` | Admin dashboard login key |
| `PORT` | `7860` | Service port |
| `ENGINE_MODE` | `hybrid` | Engine: httpx / browser / hybrid |
| `AUTO_REPLENISH` | `false` | Enable auto-registration |
| `REPLENISH_TARGET` | `30` | Target account count |
| `MOEMAIL_DOMAIN` | — | MoeMail domain (for auto-registration) |
| `MOEMAIL_KEY` | — | MoeMail API key |
| `PROXY_URL` | — | Proxy URL (for registration) |

See `.env.example` for full configuration.

## Usage

### OpenAI Compatible

```bash
curl http://localhost:7860/v1/chat/completions \
  -H "Authorization: Bearer your-api-key" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "qwen3.6-plus-nothinking",
    "messages": [{"role": "user", "content": "Hello"}],
    "stream": true
  }'
```

### Anthropic Compatible

```bash
curl http://localhost:7860/v1/messages \
  -H "x-api-key: your-api-key" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "claude-3-5-sonnet-latest",
    "messages": [{"role": "user", "content": "Hello"}],
    "max_tokens": 1024
  }'
```

### Image Generation

```bash
curl http://localhost:7860/v1/images/generations \
  -H "Authorization: Bearer your-api-key" \
  -H "Content-Type: application/json" \
  -d '{"prompt": "A cyberpunk cat", "n": 1, "size": "1024x1024"}'
```

## Admin Dashboard

Access `http://localhost:7860` for the admin panel:

- **Overview**: Request count, token usage, RPM/TPM, health timeline
- **Accounts**: Add/remove/verify accounts, batch import, JSON editor
- **Registration**: Batch register new accounts with multiple email providers
- **Settings**: Model mapping, engine mode, proxy config, auto-replenishment
- **API Keys**: Generate and manage downstream API keys

## Project Structure

```
qwen2api/
├── backend/
│   ├── api/          # API endpoints (chat/anthropic/gemini/responses/images)
│   ├── core/         # Core modules (account pool/config/engine/database)
│   └── services/     # Business services (registration/Qwen client/tool parser)
├── frontend/         # React admin dashboard
├── data/             # Runtime data (accounts/config/stats)
├── docker-compose.yml
├── Dockerfile
└── start.py          # One-click startup script
```

## License

MIT
