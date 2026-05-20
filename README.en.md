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
  Qwen AI Reverse Gateway -- OpenAI / Anthropic / Gemini API Compatible
</p>

<p align="center"><a href="README.md">中文</a> | English</p>

---

## Overview

Qwen2api exposes Alibaba's Qwen (Tongyi Qianwen) web interface as standard API endpoints. Multi-account pool rotation, automatic registration, tool calling, streaming output -- works directly with Cherry Studio, Cursor, Claude Code, Cline, New-API, and other clients.

## Key Features

- **Multi-protocol** -- OpenAI Chat Completions / Responses API / Anthropic Messages / Gemini generateContent
- **Account pool** -- Min-Heap priority scheduling, 6-state lifecycle, circuit breaker auto-fuse
- **Auto registration** -- MoeMail / TempMail / GuerrillaMail / GPTMail / YYDS (5 channels)
- **Tool calling** -- Native FC first + XML Fallback, streaming leak-prevention, loop detection
- **Thinking mode** -- Model suffix (-thinking / -nothinking) or reasoning_effort parameter
- **Image generation** -- OpenAI DALL-E compatible, auto intent detection routes to T2I
- **Accurate token stats** -- Extracts real usage from upstream SSE, not local estimation
- **Admin panel** -- Pure HTML admin UI, accounts/keys/settings/cache/register management
- **WebUI** -- Built-in web chat with multi-session and thinking display
- **Multi-engine** -- httpx direct (fast) / Camoufox browser (anti-detection) / hybrid
- **Fault tolerance** -- Auto retry with account rotation, NativeBlock detection with XML fallback

## Supported Endpoints

| Protocol | Endpoint | Function |
|----------|----------|----------|
| OpenAI | `POST /v1/chat/completions` | Chat completion (stream/non-stream/tools/thinking) |
| OpenAI | `POST /v1/responses` | Responses API (Codex / Agents) |
| OpenAI | `POST /v1/images/generations` | Image generation |
| OpenAI | `POST /v1/embeddings` | Text embeddings |
| OpenAI | `GET /v1/models` | Model list |
| Anthropic | `POST /v1/messages` | Claude compatible (tool_use / thinking) |
| Gemini | `POST /v1beta/models/{m}:generateContent` | Gemini compatible |
| Gemini | `POST /v1beta/models/{m}:streamGenerateContent` | Gemini streaming |

## Available Models

| Model | Description |
|-------|-------------|
| `qwen3.6-plus` | Primary model, auto thinking |
| `qwen3.6-plus-thinking` | Force deep thinking |
| `qwen3.6-plus-nothinking` | Fast mode, no thinking |
| `qwen3.6-max-preview` | High performance preview |
| `qwen3.6-27b` | Lightweight |
| `qwen3.6-27b-nothinking` | Lightweight fast mode |
| `qwen3.7-max-preview-thinking` | 3.7 Max preview (forced thinking) |
| `qwen3.7-plus-preview-thinking` | 3.7 Plus preview (forced thinking) |
| `qwen-image` | Image generation |

All models are real Qwen built-in models with no alias mapping.

## Quick Start

### Docker (Recommended)

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
# Edit .env to set ADMIN_KEY and mail channels
docker-compose up -d
```

### Local

```bash
# Python 3.12+
pip install -r backend/requirements.txt
playwright install chromium  # Required for registration
python start.py
```

Visit `http://localhost:7860` after startup. Default admin key: `123456`.

## Configuration

Via `.env` or environment variables:

| Variable | Default | Description |
|----------|---------|-------------|
| `ADMIN_KEY` | `123456` | Admin panel key |
| `PORT` | `7860` | Service port |
| `ENGINE_MODE` | `httpx` | httpx / browser / hybrid |
| `AUTO_REPLENISH` | `false` | Auto registration toggle |
| `REPLENISH_TARGET` | `30` | Target account count |
| `REPLENISH_PROVIDER` | - | Registration mail channel |
| `MOEMAIL_DOMAIN` | - | MoeMail domain |
| `MOEMAIL_KEY` | - | MoeMail API key |
| `TEMPMAIL_DOMAIN` | - | TempMail domain |
| `TEMPMAIL_KEY` | - | TempMail API key |
| `TEMPMAIL_SITE_PASSWORD` | - | TempMail private site password; empty means reuse `TEMPMAIL_KEY` |
| `SMARTMAIL_KEY` | - | GPTMail key (empty = public key) |
| `VIPMAIL_KEY` | - | YYDS (215.im) key |
| `PROXY_URL` | - | Registration proxy URL |
| `PROXY_ENABLED` | `false` | Enable outbound proxy |
| `IMAGE_FORMAT` | `local_md` | Image return format |
| `DEFAULT_STREAM` | `true` | Default streaming output |

See [.env.example](.env.example) for full configuration.

## Usage Examples

### OpenAI Format

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

### Tool Calling

```bash
curl http://localhost:7860/v1/chat/completions \
  -H "Authorization: Bearer your-api-key" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "qwen3.6-plus-nothinking",
    "messages": [{"role": "user", "content": "Weather in Beijing?"}],
    "tools": [{"type": "function", "function": {"name": "get_weather", "parameters": {"type": "object", "properties": {"city": {"type": "string"}}}}}]
  }'
```

### Image Generation

```bash
curl http://localhost:7860/v1/images/generations \
  -H "Authorization: Bearer your-api-key" \
  -H "Content-Type: application/json" \
  -d '{"model": "qwen-image", "prompt": "a cute cat", "size": "1024x1024"}'
```

## Admin Panel

| Page | Path | Function |
|------|------|----------|
| Accounts | `/admin/accounts` | Add/delete/verify/disable, batch import/export, disable memory |
| Settings | `/admin/config` | Engine/mail/proxy/keys/timeout/image format |
| Register | `/admin/register` | Batch registration, multi-channel, SSE progress |
| Cache | `/admin/cache` | Image cache stats and cleanup |
| WebUI | `/webui/chat` | Built-in chat interface |

## Client Integration

| Client | Configuration |
|--------|---------------|
| Cherry Studio | API Base: `http://host:7860/v1`, model: `qwen3.6-plus` |
| Cursor | Settings > Models > OpenAI API Base |
| Claude Code | `ANTHROPIC_BASE_URL=http://host:7860` |
| Cline | OpenAI Compatible, fill Base URL |
| New-API | Add channel, type OpenAI, proxy URL = this service |

## License

MIT
