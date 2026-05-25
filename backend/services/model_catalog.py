"""
model_catalog.py -- Qwen 网页模型目录缓存与 OpenAI models 格式转换
"""

import logging
import time
from typing import Any

from backend.core.config import MODEL_MAP, get_all_available_models, settings

log = logging.getLogger("qwen2api.model_catalog")


_SUFFIX_CAPABILITIES = [
    ("-nothinking", ("thinking", "think", "reasoning")),
    ("-thinking", ("thinking", "think", "reasoning")),
    ("-deep-research", ("deep_research", "deepResearch", "research", "research_mode")),
    ("-image", ("image", "image_gen", "image_generation", "t2i")),
    ("-video", ("video", "video_gen", "video_generation", "t2v")),
    ("-webdev", ("web_dev", "webdev", "web_development", "web-dev")),
    ("-slides", ("slides", "ppt", "presentation")),
]


def _openai_model(model_id: str, *, capabilities: Any = None) -> dict:
    obj = {
        "id": model_id,
        "object": "model",
        "created": 0,
        "owned_by": "qwen",
    }
    if capabilities:
        obj["capabilities"] = capabilities
    return obj


def _first_str(*values: Any) -> str:
    for value in values:
        if isinstance(value, str) and value.strip():
            return value.strip()
    return ""


def _nested(data: dict, *path: str) -> Any:
    cur: Any = data
    for key in path:
        if not isinstance(cur, dict):
            return None
        cur = cur.get(key)
    return cur


def _capability_enabled(capabilities: Any, *names: str) -> bool:
    if isinstance(capabilities, dict):
        for name in names:
            value = capabilities.get(name)
            if value is None:
                continue
            if isinstance(value, bool):
                return value
            if isinstance(value, (list, tuple, set, dict)):
                return bool(value)
            if isinstance(value, str):
                return value.lower() not in ("", "0", "false", "no", "off", "none")
            return bool(value)
    if isinstance(capabilities, (list, tuple, set)):
        normalized = {str(item).lower() for item in capabilities}
        return any(name.lower() in normalized for name in names)
    if isinstance(capabilities, str):
        lowered = capabilities.lower()
        return any(name.lower() in lowered for name in names)
    return False


def _raw_model_id(item: dict) -> str:
    info = item.get("info") if isinstance(item.get("info"), dict) else {}
    return _first_str(
        item.get("id"),
        item.get("model"),
        item.get("model_id"),
        item.get("name"),
        info.get("id"),
        info.get("model"),
        info.get("model_id"),
        info.get("name"),
    )


def _raw_capabilities(item: dict) -> Any:
    return (
        _nested(item, "info", "meta", "capabilities")
        or _nested(item, "meta", "capabilities")
        or _nested(item, "capabilities")
        or _nested(item, "info", "capabilities")
    )


def _raw_chat_type(item: dict) -> str:
    return _first_str(
        _nested(item, "info", "meta", "chat_type"),
        _nested(item, "info", "meta", "chatType"),
        _nested(item, "meta", "chat_type"),
        _nested(item, "meta", "chatType"),
        item.get("chat_type"),
        item.get("chatType"),
    )


def build_openai_model_entries(raw_models: list[dict]) -> list[dict]:
    """把 Qwen /api/models 响应转换成 OpenAI /v1/models 列表。"""
    entries: dict[str, dict] = {}
    for item in raw_models:
        if not isinstance(item, dict):
            continue
        model_id = _raw_model_id(item)
        if not model_id:
            continue
        capabilities = _raw_capabilities(item)
        chat_type = _raw_chat_type(item)
        entries[model_id] = _openai_model(model_id, capabilities=capabilities)

        for suffix, names in _SUFFIX_CAPABILITIES:
            if _capability_enabled(capabilities, *names) or any(name in chat_type for name in names):
                entries[f"{model_id}{suffix}"] = _openai_model(f"{model_id}{suffix}", capabilities=capabilities)

    return [entries[key] for key in sorted(entries)]


def fallback_openai_model_entries() -> list[dict]:
    return [_openai_model(model_id) for model_id in get_all_available_models()]


class ModelCatalog:
    def __init__(self) -> None:
        self._expires_at = 0.0
        self._entries: list[dict] = []

    def _merge_static_aliases(self, entries: list[dict]) -> list[dict]:
        by_id = {entry["id"]: entry for entry in entries}
        for model_id in get_all_available_models():
            by_id.setdefault(model_id, _openai_model(model_id))
        for alias, target in MODEL_MAP.items():
            by_id.setdefault(alias, _openai_model(alias, capabilities={"alias_for": target}))
        return [by_id[key] for key in sorted(by_id)]

    async def get_openai_models(self, qwen_client) -> list[dict]:
        now = time.time()
        if self._entries and now < self._expires_at:
            return self._entries

        account = None
        try:
            timeout = min(5, max(1, int(getattr(settings, "ACCOUNT_ACQUIRE_TIMEOUT", 60))))
            account = await qwen_client.account_pool.acquire_wait(timeout=timeout)
            if not account:
                return self._entries or fallback_openai_model_entries()

            raw_models = await qwen_client.list_models(account.token)
            entries = build_openai_model_entries(raw_models)
            if entries:
                self._entries = self._merge_static_aliases(entries)
                self._expires_at = now + max(60, int(getattr(settings, "MODEL_CATALOG_TTL_SECONDS", 1800)))
                return self._entries
        except Exception as exc:
            log.warning(f"[Models] 动态模型目录刷新失败，使用缓存/内置列表: {exc}")
        finally:
            if account is not None:
                qwen_client.account_pool.release(account, tokens_used=0)

        return self._entries or fallback_openai_model_entries()


model_catalog = ModelCatalog()
