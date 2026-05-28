"""
tool_transform.py -- prompt-facing tool definition transforms.

The public API must keep client-provided tool names. Qwen only sees short,
stable aliases and a compact parameter schema; parser code maps aliases back
before returning tool calls to clients.
"""

import hashlib
import json
import re
from typing import Any


_ALIAS_PREFIX = "u_"
_MAX_ALIAS_LEN = 64
_IDENTIFIER = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")


def prepare_tool_defs_for_model(tool_defs: list[dict]) -> list[dict]:
    """Return tool defs using model-facing aliases while preserving originals."""
    alias_by_name = _make_aliases(tool_defs)
    prepared: list[dict] = []
    for tool in tool_defs:
        original_name = str(tool.get("name", "") or "")
        if not original_name:
            prepared.append(dict(tool))
            continue

        alias = alias_by_name[original_name]
        prepared_tool = dict(tool)
        prepared_tool["_original_name"] = original_name
        prepared_tool["_qwen_name"] = alias
        prepared_tool["name"] = alias
        prepared.append(prepared_tool)
    return prepared


def resolve_model_tool_name(name: str, tools: list[dict]) -> str:
    """Resolve an original or alias tool name to the model-facing alias."""
    matched = _find_tool_by_name(name, tools)
    if matched:
        return str(matched.get("_qwen_name") or matched.get("name") or name)
    return name


def resolve_original_tool_name(name: str, tools: list[dict]) -> str | None:
    """Resolve a model-facing alias or legacy original name to the client name."""
    matched = _find_tool_by_name(name, tools)
    if matched:
        return str(matched.get("_original_name") or matched.get("name") or name)
    return None


def get_tool_original_name(tool: dict) -> str:
    return str(tool.get("_original_name") or tool.get("name") or "")


def get_tool_model_name(tool: dict) -> str:
    return str(tool.get("_qwen_name") or tool.get("name") or "")


def format_compact_schema(schema: Any) -> str:
    """Render JSON Schema as a compact, prompt-friendly argument shape."""
    if not isinstance(schema, dict) or not schema:
        return "{}"

    properties = schema.get("properties")
    if isinstance(properties, dict):
        return _format_object_schema(schema, depth=0)

    schema_type = _schema_type(schema, depth=0)
    return schema_type or "object"


def _make_aliases(tool_defs: list[dict]) -> dict[str, str]:
    used: set[str] = set()
    aliases: dict[str, str] = {}
    for tool in tool_defs:
        name = str(tool.get("name", "") or "")
        if not name:
            continue

        alias = _fit_alias(f"{_ALIAS_PREFIX}{_short_hash(name)}", name)
        if alias in used:
            alias = _fit_alias(f"{alias}_{len(used) + 1}", name)

        counter = 2
        while alias in used:
            alias = _fit_alias(f"{_ALIAS_PREFIX}{_short_hash(name)}_{counter}", name)
            counter += 1

        used.add(alias)
        aliases[name] = alias
    return aliases


def _fit_alias(alias: str, source: str) -> str:
    if len(alias) <= _MAX_ALIAS_LEN:
        return alias
    suffix = f"_{_short_hash(source)}"
    head_len = _MAX_ALIAS_LEN - len(suffix)
    return f"{alias[:head_len]}{suffix}"


def _short_hash(value: str) -> str:
    return hashlib.sha1(value.encode("utf-8")).hexdigest()[:8]


def _find_tool_by_name(name: str, tools: list[dict]) -> dict | None:
    if not name:
        return None

    for tool in tools:
        candidates = {
            str(tool.get("name") or ""),
            str(tool.get("_qwen_name") or ""),
            str(tool.get("_original_name") or ""),
        }
        if name in candidates:
            return tool

    lowered = name.lower()
    for tool in tools:
        candidates = {
            str(tool.get("name") or ""),
            str(tool.get("_qwen_name") or ""),
            str(tool.get("_original_name") or ""),
        }
        if lowered in {candidate.lower() for candidate in candidates if candidate}:
            return tool

    return None


def _format_object_schema(schema: dict, depth: int) -> str:
    properties = schema.get("properties") or {}
    if not isinstance(properties, dict) or not properties:
        additional = schema.get("additionalProperties")
        if isinstance(additional, dict):
            return f"Record<string, {_schema_type(additional, depth + 1)}>"
        return "{}"

    required = set(schema.get("required") or [])
    lines = ["{"]
    for key, subschema in properties.items():
        optional = "" if key in required else "?"
        field_type = _schema_type(subschema, depth + 1)
        comment = _schema_comment(subschema)
        suffix = f" // {comment}" if comment else ""
        lines.append(f"  {_format_key(str(key))}{optional}: {field_type}{suffix}")
    lines.append("}")
    return "\n".join(lines)


def _schema_type(schema: Any, depth: int) -> str:
    if not isinstance(schema, dict):
        return "any"

    if "const" in schema:
        return _json_literal(schema["const"])

    enum_values = schema.get("enum")
    if isinstance(enum_values, list) and enum_values:
        rendered = " | ".join(_json_literal(v) for v in enum_values[:8])
        if len(enum_values) > 8:
            rendered += " | ..."
        return rendered

    for union_key in ("anyOf", "oneOf", "allOf"):
        variants = schema.get(union_key)
        if isinstance(variants, list) and variants:
            return " | ".join(_schema_type(item, depth + 1) for item in variants[:6])

    schema_type = schema.get("type")
    if isinstance(schema_type, list):
        return " | ".join(_map_schema_type(t, schema, depth) for t in schema_type)
    if isinstance(schema_type, str):
        return _map_schema_type(schema_type, schema, depth)
    if isinstance(schema.get("properties"), dict):
        return _inline_object_type(schema, depth)
    if isinstance(schema.get("items"), dict):
        return f"Array<{_schema_type(schema['items'], depth + 1)}>"
    return "any"


def _map_schema_type(schema_type: str, schema: dict, depth: int) -> str:
    if schema_type == "object":
        return _inline_object_type(schema, depth)
    if schema_type == "array":
        items = schema.get("items")
        item_type = _schema_type(items, depth + 1) if isinstance(items, dict) else "any"
        return f"Array<{item_type}>"
    if schema_type in {"string", "number", "integer", "boolean", "null"}:
        return schema_type
    return schema_type or "any"


def _inline_object_type(schema: dict, depth: int) -> str:
    properties = schema.get("properties")
    if not isinstance(properties, dict) or not properties:
        additional = schema.get("additionalProperties")
        if isinstance(additional, dict):
            return f"Record<string, {_schema_type(additional, depth + 1)}>"
        return "object"

    if depth >= 2 or len(properties) > 4:
        return "object"

    required = set(schema.get("required") or [])
    parts = []
    for key, subschema in properties.items():
        optional = "" if key in required else "?"
        parts.append(f"{_format_key(str(key))}{optional}: {_schema_type(subschema, depth + 1)}")
    return "{ " + "; ".join(parts) + " }"


def _schema_comment(schema: Any) -> str:
    if not isinstance(schema, dict):
        return ""

    parts: list[str] = []
    description = schema.get("description") or schema.get("title")
    if description:
        normalized = " ".join(str(description).split())
        if len(normalized) > 120:
            normalized = normalized[:117].rstrip() + "..."
        parts.append(normalized)

    if "default" in schema:
        parts.append(f"default={_json_literal(schema['default'])}")

    return "; ".join(parts)


def _format_key(key: str) -> str:
    if _IDENTIFIER.match(key):
        return key
    return json.dumps(key, ensure_ascii=False)


def _json_literal(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False)
