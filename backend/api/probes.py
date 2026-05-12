"""
probes.py -- 健康检查与模型列表
"""

import time
from fastapi import APIRouter, Request
from backend.core.config import MODEL_MAP, VERSION, BUILTIN_MODELS, DEFAULT_MODEL_ALIASES, get_all_available_models

router = APIRouter()


@router.get("/health")
@router.get("/healthz")
async def health():
    return {"status": "ok", "version": VERSION}


@router.get("/v1/models")
@router.get("/models")
async def list_models():
    """返回兼容 OpenAI /v1/models 格式的模型列表。包含内置模型 + 默认别名 + 用户自定义映射。"""
    all_names = get_all_available_models()
    data = []
    for name in all_names:
        data.append({
            "id": name,
            "object": "model",
            "created": 1700000000,
            "owned_by": "qwen2api",
        })
    return {"object": "list", "data": data}
