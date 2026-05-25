import os
import json
import logging
from dataclasses import dataclass
from pathlib import Path
from pydantic_settings import BaseSettings

BASE_DIR = Path(__file__).resolve().parent.parent.parent
DATA_DIR = BASE_DIR / "data"

class Settings(BaseSettings):
    # 服务配置
    PORT: int = int(os.getenv("PORT", 7860))
    WORKERS: int = int(os.getenv("WORKERS", 3))
    ADMIN_KEY: str = os.getenv("ADMIN_KEY", "123456")  # 默认管理密钥
    REGISTER_SECRET: str = os.getenv("REGISTER_SECRET", "")
    APP_URL: str = os.getenv("APP_URL", "")  # 应用对外 URL，用于图片代理等

    # MoeMail 自建配置
    MOEMAIL_DOMAIN: str = os.getenv("MOEMAIL_DOMAIN", "")
    MOEMAIL_KEY: str = os.getenv("MOEMAIL_KEY", "")

    # TempMail (awsl.uk) 自建配置
    TEMPMAIL_DOMAIN: str = os.getenv("TEMPMAIL_DOMAIN", "")
    TEMPMAIL_KEY: str = os.getenv("TEMPMAIL_KEY", "")
    TEMPMAIL_SITE_PASSWORD: str = os.getenv("TEMPMAIL_SITE_PASSWORD", "")

    # SmartMail (mail.chatgpt.org.uk) 配置
    SMARTMAIL_KEY: str = os.getenv("SMARTMAIL_KEY", "")

    # VipMail (vip.215.im) 配置
    VIPMAIL_KEY: str = os.getenv("VIPMAIL_KEY", "")

    # 引擎模式：httpx（快速直连）、browser（浏览器指纹，防封）或 hybrid（混合）
    ENGINE_MODE: str = os.getenv("ENGINE_MODE", "hybrid")
    NATIVE_TOOL_PASSTHROUGH: bool = os.getenv("NATIVE_TOOL_PASSTHROUGH", "true").lower() in ("1", "true", "yes", "on")
    # 浏览器引擎配置
    BROWSER_POOL_SIZE: int = int(os.getenv("BROWSER_POOL_SIZE", 2))
    MAX_INFLIGHT_PER_ACCOUNT: int = int(os.getenv("MAX_INFLIGHT", 1))
    MAX_WAITING_REQUESTS: int = int(os.getenv("MAX_WAITING_REQUESTS", 100))
    ACCOUNT_ACQUIRE_TIMEOUT: int = int(os.getenv("ACCOUNT_ACQUIRE_TIMEOUT", 60))
    STREAM_KEEPALIVE_INTERVAL: int = int(os.getenv("STREAM_KEEPALIVE_INTERVAL", 5))
    # 流式输出打字机效果：每批输出的字符数和间隔（毫秒）
    # 设为 0 则直接透传上游原始速度（无打字机效果）
    STREAM_MIN_CHUNK_SIZE: int = int(os.getenv("STREAM_MIN_CHUNK_SIZE", 1))  # 每次输出最少字符数
    STREAM_MAX_CHUNK_SIZE: int = int(os.getenv("STREAM_MAX_CHUNK_SIZE", 4))  # 每次输出最多字符数
    STREAM_CHUNK_DELAY_MS: int = int(os.getenv("STREAM_CHUNK_DELAY_MS", 30))  # 每批之间延迟(ms)
    # 默认流式回复：True=默认流式，False=看客户端 stream 字段
    DEFAULT_STREAM: bool = os.getenv("DEFAULT_STREAM", "true").lower() in ("1", "true", "yes", "on")

    # 容灾与限流
    MAX_RETRIES: int = 3
    TOOL_MAX_RETRIES: int = 4
    EMPTY_RESPONSE_RETRIES: int = 1
    # 思考模式：True=默认开启（慢但质量高），False=默认关闭（快但可能质量略低）
    DEFAULT_THINKING_ENABLED: bool = os.getenv("DEFAULT_THINKING_ENABLED", "false").lower() in ("1", "true", "yes", "on")
    ACCOUNT_MIN_INTERVAL_MS: int = int(os.getenv("ACCOUNT_MIN_INTERVAL_MS", 300))
    REQUEST_JITTER_MIN_MS: int = int(os.getenv("REQUEST_JITTER_MIN_MS", 30))
    REQUEST_JITTER_MAX_MS: int = int(os.getenv("REQUEST_JITTER_MAX_MS", 100))
    RATE_LIMIT_BASE_COOLDOWN: int = int(os.getenv("RATE_LIMIT_BASE_COOLDOWN", 600))
    RATE_LIMIT_MAX_COOLDOWN: int = int(os.getenv("RATE_LIMIT_MAX_COOLDOWN", 3600))
    RATE_LIMIT_COOLDOWN: int = RATE_LIMIT_BASE_COOLDOWN

    # AccountPool v2 — 高并发调度
    MAX_RPM_PER_ACCOUNT: int = int(os.getenv("MAX_RPM_PER_ACCOUNT", 50))
    MAX_TPM_PER_ACCOUNT: int = int(os.getenv("MAX_TPM_PER_ACCOUNT", 500000))
    CIRCUIT_BREAKER_THRESHOLD: int = int(os.getenv("CIRCUIT_BREAKER_THRESHOLD", 5))
    ACCOUNT_WARMUP_MINUTES: int = int(os.getenv("ACCOUNT_WARMUP_MINUTES", 120))

    # 自动补号
    AUTO_REPLENISH: bool = os.getenv("AUTO_REPLENISH", "false").lower() in ("1", "true", "yes", "on")
    REPLENISH_TARGET: int = int(os.getenv("REPLENISH_TARGET", 30))
    REPLENISH_CONCURRENCY: int = int(os.getenv("REPLENISH_CONCURRENCY", 3))
    REPLENISH_PROVIDER: str = os.getenv("REPLENISH_PROVIDER", "")

    # 限流应急补号
    AUTO_REPLENISH_ON_EXHAUST: bool = os.getenv("AUTO_REPLENISH_ON_EXHAUST", "true").lower() in ("1", "true", "yes", "on")
    REPLENISH_EXHAUST_COUNT: int = int(os.getenv("REPLENISH_EXHAUST_COUNT", 10))
    REPLENISH_EXHAUST_CONCURRENCY: int = int(os.getenv("REPLENISH_EXHAUST_CONCURRENCY", 3))

    # 响应缓存
    CACHE_TTL_SECONDS: int = int(os.getenv("CACHE_TTL_SECONDS", 60))
    CACHE_MAX_SIZE: int = int(os.getenv("CACHE_MAX_SIZE", 500))

    # 竞速模式
    RACING_ENABLED: bool = os.getenv("RACING_ENABLED", "false").lower() in ("1", "true", "yes", "on")

    # 注册代理池（用于绕过 WAF 频率限制）
    PROXY_ENABLED: bool = os.getenv("PROXY_ENABLED", "false").lower() in ("1", "true", "yes", "on")
    PROXY_URL: str = os.getenv("PROXY_URL", "")              # e.g. http://host:port  socks5://host:port
    PROXY_USERNAME: str = os.getenv("PROXY_USERNAME", "")   # 为空则无需认证
    PROXY_PASSWORD: str = os.getenv("PROXY_PASSWORD", "")   # 为空则无需认证

    # 日志配置
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")
    LOG_MAX_DAYS: int = int(os.getenv("LOG_MAX_DAYS", 7))

    # 请求超时配置（秒）
    TIMEOUT_CHAT: int = int(os.getenv("TIMEOUT_CHAT", 60))
    TIMEOUT_IMAGE: int = int(os.getenv("TIMEOUT_IMAGE", 60))
    TIMEOUT_STREAM_IDLE: int = int(os.getenv("TIMEOUT_STREAM_IDLE", 60))
    TIMEOUT_REGISTER: int = int(os.getenv("TIMEOUT_REGISTER", 60))

    # WebUI 配置
    WEBUI_ENABLED: bool = os.getenv("WEBUI_ENABLED", "true").lower() in ("1", "true", "yes", "on")
    WEBUI_KEY: str = os.getenv("WEBUI_KEY", "")

    # 图片返回格式：qwen_url / local_url / qwen_md / local_md / base64
    IMAGE_FORMAT: str = os.getenv("IMAGE_FORMAT", "local_md")
    # 图片缓存上限（MB），0=不限制
    IMAGE_CACHE_MAX_MB: int = int(os.getenv("IMAGE_CACHE_MAX_MB", 100))

    # Qwen 网页模型目录与请求头参数
    MODEL_CATALOG_TTL_SECONDS: int = int(os.getenv("MODEL_CATALOG_TTL_SECONDS", 1800))
    ENABLE_SPECIAL_CHAT_MODES: bool = os.getenv("ENABLE_SPECIAL_CHAT_MODES", "true").lower() in ("1", "true", "yes", "on")
    QWEN_CHROME_VERSION: str = os.getenv("QWEN_CHROME_VERSION", "124")
    QWEN_WEB_VERSION: str = os.getenv("QWEN_WEB_VERSION", "0.2.46")
    QWEN_BX_V: str = os.getenv("QWEN_BX_V", "")
    QWEN_IMPERSONATE: str = os.getenv("QWEN_IMPERSONATE", f"chrome{os.getenv('QWEN_CHROME_VERSION', '124')}")


    # 数据文件路径
    ACCOUNTS_FILE: str = os.getenv("ACCOUNTS_FILE", str(DATA_DIR / "accounts.json"))
    USERS_FILE: str = os.getenv("USERS_FILE", str(DATA_DIR / "users.json"))
    CAPTURES_FILE: str = os.getenv("CAPTURES_FILE", str(DATA_DIR / "captures.json"))
    CONFIG_FILE: str = os.getenv("CONFIG_FILE", str(DATA_DIR / "config.json"))

    class Config:
        env_file = ".env"

API_KEYS_FILE = DATA_DIR / "api_keys.json"

def load_api_keys() -> set:
    if API_KEYS_FILE.exists():
        try:
            with open(API_KEYS_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                return set(data.get("keys", []))
        except Exception:
            pass
    return set()

def save_api_keys(keys: set):
    API_KEYS_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(API_KEYS_FILE, "w", encoding="utf-8") as f:
        json.dump({"keys": list(keys)}, f, indent=2)

# 在内存中存储管理的 API Keys
API_KEYS = load_api_keys()

VERSION = "2.0.0"

settings = Settings()

# ── 运行时设置持久化（UI 层修改的设置保存到 config.json）──
_RUNTIME_CONFIG_FILE = DATA_DIR / "runtime_settings.json"
_PERSIST_KEYS = [
    "ADMIN_KEY", "APP_URL",
    "AUTO_REPLENISH", "REPLENISH_TARGET", "REPLENISH_CONCURRENCY", "REPLENISH_PROVIDER",
    "AUTO_REPLENISH_ON_EXHAUST", "REPLENISH_EXHAUST_COUNT", "REPLENISH_EXHAUST_CONCURRENCY",
    "MAX_INFLIGHT_PER_ACCOUNT", "MAX_WAITING_REQUESTS", "ACCOUNT_ACQUIRE_TIMEOUT",
    "MAX_RPM_PER_ACCOUNT", "MAX_TPM_PER_ACCOUNT",
    "CACHE_TTL_SECONDS", "RACING_ENABLED", "ENGINE_MODE", "DEFAULT_STREAM",
    "MODEL_CATALOG_TTL_SECONDS", "ENABLE_SPECIAL_CHAT_MODES",
    "QWEN_CHROME_VERSION", "QWEN_WEB_VERSION", "QWEN_BX_V", "QWEN_IMPERSONATE",
    "MOEMAIL_DOMAIN", "MOEMAIL_KEY", "TEMPMAIL_DOMAIN", "TEMPMAIL_KEY", "TEMPMAIL_SITE_PASSWORD",
    "SMARTMAIL_KEY", "VIPMAIL_KEY",
    "PROXY_ENABLED", "PROXY_URL", "PROXY_USERNAME", "PROXY_PASSWORD",
    "LOG_LEVEL", "LOG_MAX_DAYS",
    "TIMEOUT_CHAT", "TIMEOUT_IMAGE", "TIMEOUT_STREAM_IDLE", "TIMEOUT_REGISTER",
    "WEBUI_ENABLED", "WEBUI_KEY",
    "IMAGE_FORMAT", "IMAGE_CACHE_MAX_MB",
]

def save_runtime_settings():
    """将 UI 修改的运行时设置持久化到文件"""
    data = {}
    for key in _PERSIST_KEYS:
        val = getattr(settings, key, None)
        if val is not None:
            data[key] = val
    try:
        _RUNTIME_CONFIG_FILE.parent.mkdir(parents=True, exist_ok=True)
        with open(_RUNTIME_CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
    except Exception as e:
        logging.getLogger("qwen2api").warning(f"保存运行时设置失败: {e}")

def _load_runtime_settings():
    """启动时从文件恢复 UI 修改的运行时设置"""
    if not _RUNTIME_CONFIG_FILE.exists():
        return
    try:
        with open(_RUNTIME_CONFIG_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        for key, val in data.items():
            if key == "MODEL_MAP":
                continue  # 不再加载模型映射
            if key in _PERSIST_KEYS and hasattr(settings, key):
                expected_type = type(getattr(settings, key))
                try:
                    setattr(settings, key, expected_type(val))
                except (ValueError, TypeError):
                    pass
        logging.getLogger("qwen2api").info(f"[Config] 已从 runtime_settings.json 恢复 {len(data)} 项运行时设置")
    except Exception as e:
        logging.getLogger("qwen2api").warning(f"加载运行时设置失败: {e}")

# ── Qwen 官网内置可用模型 ──────────────────────────────────────────────────────
BUILTIN_MODELS = [
    "qwen3.6-plus",
    "qwen3.6-plus-thinking",
    "qwen3.6-plus-nothinking",
    "qwen3.6-max-preview",
    "qwen3.6-max-preview-thinking",
    "qwen3.6-max-preview-nothinking",
    "qwen3.6-27b",
    "qwen3.6-27b-thinking",
    "qwen3.6-27b-nothinking",
    # Qwen 3.7 系列（仅支持思考模式）
    "qwen3.7-max-preview-thinking",
    "qwen3.7-plus-preview-thinking",
    # 生图专用模型
    "qwen-image",
]

# 默认模型（未知模型名的 fallback）
DEFAULT_MODEL = "qwen3.6-plus"

# 思考模式后缀
NOTHINKING_SUFFIX = "-nothinking"
THINKING_SUFFIX = "-thinking"

MODEL_MODE_SUFFIXES = [
    (NOTHINKING_SUFFIX, "t2t", False),
    (THINKING_SUFFIX, "t2t", True),
    ("-deep-research", "deep_research", None),
    ("-web-dev", "web_dev", None),
    ("-webdev", "web_dev", None),
    ("-slides", "slides", None),
    ("-video", "t2v", None),
    ("-t2v", "t2v", None),
    ("-image", "t2i", None),
    ("-t2i", "t2i", None),
]


@dataclass(frozen=True)
class ModelResolution:
    requested: str
    model: str
    chat_mode: str
    thinking: bool | None
    suffix: str | None = None

# ── 默认别名映射（已禁用，不再做模型映射）──────────────
DEFAULT_MODEL_ALIASES: dict[str, str] = {}

# 用户自定义映射（管理后台配置，优先级最高）
MODEL_MAP: dict = {}

# 启动时从持久化文件恢复（包括 MODEL_MAP）
_load_runtime_settings()

# 图片生成沿用网页当前真实可用的基础模型
IMAGE_MODEL_DEFAULT = "qwen3.6-plus"


def resolve_model_request(name: str) -> ModelResolution:
    """解析客户端模型名，得到 Qwen 模型、chat_mode 与 thinking 覆盖。"""
    requested = name or DEFAULT_MODEL
    mapped = MODEL_MAP.get(requested, requested)
    base_name = mapped
    chat_mode = "t2t"
    thinking: bool | None = None
    suffix: str | None = None

    if settings.ENABLE_SPECIAL_CHAT_MODES:
        for mode_suffix, mode, forced_thinking in MODEL_MODE_SUFFIXES:
            if mapped.endswith(mode_suffix):
                base_name = mapped[:-len(mode_suffix)]
                chat_mode = mode
                thinking = forced_thinking
                suffix = mode_suffix
                break
    elif mapped.endswith(NOTHINKING_SUFFIX):
        base_name = mapped[:-len(NOTHINKING_SUFFIX)]
        thinking = False
        suffix = NOTHINKING_SUFFIX
    elif mapped.endswith(THINKING_SUFFIX):
        base_name = mapped[:-len(THINKING_SUFFIX)]
        thinking = True
        suffix = THINKING_SUFFIX

    if mapped == "qwen-image":
        base_name = mapped
        chat_mode = "t2i"

    qwen37_map = {
        "qwen3.7-max-preview-thinking": "qwen-latest-series-invite-beta-v24",
        "qwen3.7-max-preview": "qwen-latest-series-invite-beta-v24",
        "qwen3.7-plus-preview-thinking": "qwen-latest-series-invite-beta-v16",
        "qwen3.7-plus-preview": "qwen-latest-series-invite-beta-v16",
    }
    model = qwen37_map.get(base_name, qwen37_map.get(mapped, base_name))
    if "qwen3.7" in base_name or "qwen3.7" in mapped:
        thinking = True

    return ModelResolution(
        requested=requested,
        model=model,
        chat_mode=chat_mode,
        thinking=thinking,
        suffix=suffix,
    )


def resolve_model(name: str) -> str:
    """解析模型名，返回 Qwen 真实模型名。

    -nothinking / -thinking 后缀会被剥离，真实模型名传给 Qwen。
    思考模式由 resolve_model_thinking() 单独判断。
    """
    return resolve_model_request(name).model


def resolve_model_thinking(name: str) -> bool | None:
    """根据模型名判断思考模式。

    -nothinking 后缀 = False（快速模式，关闭思考）
    -thinking 后缀 = True（强制思考模式）
    无后缀 = None（自动模式，由 Qwen 决定）
    Qwen 3.7 系列 = 始终 True（仅支持思考模式）
    """
    return resolve_model_request(name).thinking


def get_all_available_models() -> list[str]:
    """获取所有可用模型名（内置模型 + 用户自定义映射）。"""
    all_names = set(BUILTIN_MODELS)
    all_names.update(MODEL_MAP.keys())
    all_names.update(MODEL_MAP.values())
    return sorted(all_names)


def validate_security_config():
    """启动时校验安全相关配置。"""
    _log = logging.getLogger("qwen2api.config")
    if not settings.ADMIN_KEY:
        _log.warning("[Security] ADMIN_KEY 未配置，使用默认值 123456")
        settings.ADMIN_KEY = "123456"
